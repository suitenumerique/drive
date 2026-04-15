/**
 * OnlyOffice client-side editor for encrypted files.
 *
 * Loads the OnlyOffice editor directly in the browser (no WOPI, no Document Server).
 * File content is decrypted client-side via the vault, edited locally,
 * and auto-saved back to S3 encrypted.
 *
 * Flow:
 * 1. Download encrypted file from S3
 * 2. Decrypt via vault (with key chain)
 * 3. Convert to .bin via x2t WASM (in-memory)
 * 4. Load OnlyOffice with blob URL
 * 5. connectMockServer() with our bridge
 * 6. Auto-save: extract .bin → x2t → original format → encrypt → upload S3
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader } from '@gouvfr-lasuite/cunningham-react';
import { Item } from '@/features/drivers/types';
import { getDriver } from '@/features/config/Config';
import { fetchAPI } from '@/features/api/fetchApi';
import {
  convertToInternal,
  convertFromInternal,
  convertFromInternalToPdf,
} from './x2tConverter';
import { EXTENSION_TO_X2T_TYPE } from './types';
import {
  createMockServerCallbacks,
  sendToEditor,
  setEditorInstance,
  setVerboseSends,
} from './mockServer';
import {
  initLocalUser,
  getUniqueOOId,
  addRemoteUser,
  removeRemoteUser,
  buildConnectStateMessage,
  getRemoteOOInternalId,
} from './participants';
import {
  resetPatchIndex,
  observeIncomingSaveChanges,
} from './changesPipeline';
import { EncryptedRelay } from './encryptedRelay';
import { withIncomingOTGate } from './incomingOtGate';
import {
  acquireCellLock,
  releaseCellLock,
  releaseAllUserLocks,
  acquireSaveLock,
  releaseSaveLock,
  isSaveLocked,
  resetAllLocks,
} from './locks';
import {
  initCheckpointing,
  stopCheckpointing,
  forceSave,
  hasUnsavedChanges,
  markRemoteSaveCommitted,
} from './checkpointing';
import {
  MIME_TO_DOC_TYPE,
  MIME_TO_OO_FILE_TYPE,
  MIME_TO_X2T_TYPE,
  MIME_TO_EXTENSION,
  type OOConfig,
} from './types';
import { useAuth } from '@/features/auth/Auth';
import styles from './OOEditor.module.scss';

// The OnlyOffice DocsAPI is loaded as a global from the static assets
declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (
        placeholder: string,
        config: OOConfig
      ) => OOEditorInstance;
    };
  }
}

interface OOEditorInstance {
  connectMockServer: (callbacks: any) => void;
  sendMessageToOO: (msg: any) => void;
  asc_nativeGetFile: () => Uint8Array;
  destroyEditor: () => void;
}

interface OOEditorProps {
  item: Item;
}

type EditorState =
  | 'loading'
  | 'decrypting'
  | 'converting'
  | 'syncing-history'
  | 'mounting'
  | 'ready'
  | 'error'
  | 'stale-resyncing'
  | 'oo-crashed';

// Only these OO message types are allowed in from peers. Anything else (rpc,
// executeCommand, documentOpen, pluginEvent, forceSave, …) would be a way for
// a malicious peer to reach internal OO surfaces that aren't meant to be
// peer-driven, so the bridge drops them.
const INBOUND_ALLOWLIST: ReadonlySet<string> = new Set([
  'saveChanges',
  'cursor',
  'message',
  'meta',
  'getLock',
  'releaseLock',
  'connectState',
  'authChanges',
]);

function sendToEditorGuarded(msg: { type?: string } & Record<string, unknown>) {
  if (!msg || typeof msg.type !== 'string' || !INBOUND_ALLOWLIST.has(msg.type)) {
    console.warn(
      '[OOEditor] dropping inbound message with disallowed type:',
      msg?.type,
    );
    return;
  }
  sendToEditor(msg as any);
}

export const OOEditor = ({ item }: OOEditorProps) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [state, setState] = useState<EditorState>('loading');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [relayFailed, setRelayFailed] = useState(false);
  /**
   * Bumped when the relay tells us our history cursor is stale (close
   * code 4001). Each bump re-runs the init effect, which refetches the
   * S3 snapshot and builds a fresh editor. The old editor + relay are
   * torn down in the cleanup branch of the previous run.
   */
  const [reinitKey, setReinitKey] = useState(0);
  const editorRef = useRef<OOEditorInstance | null>(null);
  const relayRef = useRef<EncryptedRelay | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptLoadedRef = useRef(false);
  // Connected peers with edit capability (not including self). Keyed
  // by userId, value is the earliest `joinedAt` we've seen for that
  // user — so leader election can tiebreak across multiple same-user
  // tabs by comparing (userId, joinedAt) lexicographically.
  const editorPeersRef = useRef<Map<string, number>>(new Map());
  // Reference to the inner OO iframe's window — used to register media in
  // g_oDocumentUrls when inbound saveChanges envelopes carry inline images.
  const innerWindowRef = useRef<any>(null);
  /**
   * Remote saveChanges envelopes that arrived before OO finished loading
   * the base document. OO silently drops external saveChanges that land
   * before `onDocumentReady`, so we hold them in order and drain once the
   * editor is ready. Critical for the history-replay path on join: the
   * relay dumps every pending change immediately after WS open, often
   * before OO has mounted the document.
   */
  const pendingRemoteChangesRef = useRef<Array<() => void>>([]);
  const documentReadyRef = useRef(false);

  /**
   * Drain pre-delay: once OO reports the document content ready, we
   * still wait this long before feeding it the first replayed event,
   * so its internal state machine has time to settle.
   */
  const DRAIN_PRE_DELAY_MS = 0;

  /**
   * FIFO buffer of inbound `saveChanges` apply-closures collected while
   * the post-ready pre-delay is still active. Flushed in arrival order
   * when the pre-delay elapses.
   */
  const replayBufferRef = useRef<Array<() => void>>([]);

  /**
   * Once this flips to true, every outbound event callback (saveChanges,
   * cursor, lock, message, meta) short-circuits before touching the
   * relay. It's flipped whenever we detect the OO editor has entered
   * an inconsistent state (crash overlay shown). The underlying OO
   * instance may keep running its autosave loop and emitting edits
   * built from its corrupted in-memory state — we must NOT let those
   * leak to peers, or they'd crash everyone in the room.
   */
  const outgoingSilencedRef = useRef(false);

  /**
   * Deterministic leader election: lexicographically lowest
   * (userId, joinedAt) among connected editors wins. Readers never
   * lead. Every client computes this independently — no coordination.
   * Exposed as a ref so both `initCheckpointing` and the beforeunload
   * handler can call it.
   */
  const isSaveLeaderRef = useRef<() => boolean>(() => false);

  /**
   * Enter the crash-recovery state: silence all outbound events to
   * the relay AND flip `state` to render the overlay. Use this
   * instead of calling `setState('oo-crashed')` directly so we never
   * forget to cut off outbound traffic.
   */
  const enterCrashState = useCallback(() => {
    if (!outgoingSilencedRef.current) {
      console.warn(
        '[OOEditor] entering crash state — outbound traffic silenced',
      );
    }
    outgoingSilencedRef.current = true;
    setState('oo-crashed');
  }, []);

  /**
   * Crash-recovery reload: before bumping `reinitKey` (which re-runs
   * the init effect and refetches the S3 snapshot), ask the room's
   * save-leader to persist immediately. Then wait for the
   * `save:committed` broadcast to arrive before bumping — that's the
   * signal the S3 object has a fresh `x-amz-meta-epoch` we can pick
   * up. A hard timeout falls through to a reinit against the old
   * epoch if no one saves in time.
   *
   * While the wait is in progress the button shows a loader and is
   * disabled so the user can't double-click.
   */
  const RECOVERY_SAVE_WAIT_MS = 10000;
  const [recoveryWaiting, setRecoveryWaiting] = useState(false);
  /** Fired by the onRemoteSaveCommitted callback if non-null. */
  const recoveryResolveRef = useRef<(() => void) | null>(null);

  const requestRecoveryReload = useCallback(() => {
    if (recoveryWaiting) return;
    setRecoveryWaiting(true);
    try {
      relayRef.current?.sendNeedsSave();
    } catch (e) {
      console.warn('[OOEditor] sendNeedsSave failed', e);
    }
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      recoveryResolveRef.current = null;
      setRecoveryWaiting(false);
      setState('stale-resyncing');
      setReinitKey(k => k + 1);
    };
    // Resolved by onRemoteSaveCommitted the moment a fresh save lands.
    recoveryResolveRef.current = finish;
    // Hard timeout: fall through even if no save arrives.
    setTimeout(finish, RECOVERY_SAVE_WAIT_MS);
  }, [recoveryWaiting]);

  /**
   * One-shot pre-delay timer that releases replay after OO settles.
   * While true, saveChanges are buffered; when it flips to false they
   * flow straight through.
   */
  const replayPreDelayActiveRef = useRef(true);

  /**
   * Entry point for every inbound `saveChanges`. Classifies against
   * the expected index and either applies in place, or buffers for
   * later. Non-saveChanges events skip this entirely.
   */
  const handleIncomingSaveChanges = useCallback(
    (message: Record<string, unknown>, applyFn: () => void) => {
      // We apply every inbound `saveChanges` in receive order, full stop.
      // - Ordering is already guaranteed by the relay (TCP + our handler
      //   serialization in `encryptedRelay.ts`).
      // - OO's own collaborative-edit engine handles any residual
      //   sequence bookkeeping.
      // - Trying to arbitrate ordering ourselves caused false "stale"
      //   drops on sender-session resets and phantom gaps that never
      //   close.
      //
      // During the pre-delay window we still hold events back (so OO
      // has a moment to settle after onDocumentContentReady), then
      // flush them in arrival order when the timer fires.
      if (replayPreDelayActiveRef.current) {
        replayBufferRef.current.push(applyFn);
        return;
      }
      try {
        applyFn();
      } catch (e) {
        console.warn('[replay] apply error', e);
      }
    },
    [],
  );

  /**
   * Called once OO reports documentContentReady. Waits the pre-delay
   * then flushes the FIFO buffer in arrival order.
   */
  const releaseReplayAfterPreDelay = useCallback(() => {
    console.log(
      `[replay] scheduling release after ${DRAIN_PRE_DELAY_MS} ms pre-delay ` +
        `(buffered=${replayBufferRef.current.length})`,
    );
    setTimeout(() => {
      console.log(
        '[replay] pre-delay elapsed — flushing',
        replayBufferRef.current.length,
        'buffered events in arrival order',
      );
      replayPreDelayActiveRef.current = false;
      setVerboseSends(true);
      const queue = replayBufferRef.current;
      replayBufferRef.current = [];
      for (const apply of queue) {
        try {
          apply();
        } catch (e) {
          console.warn('[replay] flush apply error', e);
        }
      }
    }, DRAIN_PRE_DELAY_MS);
  }, []);
  const canEdit = !!item.abilities?.partial_update;

  const mime = item.mimetype || '';
  const docType = MIME_TO_DOC_TYPE[mime] || 'text';
  const ooFileType = MIME_TO_OO_FILE_TYPE[mime] || 'docx';
  const x2tType = MIME_TO_X2T_TYPE[mime] || 'doc';
  // x2t needs a filename with the correct extension for conversion
  const x2tExtension = MIME_TO_EXTENSION[mime] || 'docx';
  const filename = `document.${x2tExtension}`;

  /**
   * Load the OnlyOffice API script if not already loaded.
   */
  const loadOOScript = useCallback((): Promise<void> => {
    if (window.DocsAPI) return Promise.resolve();
    if (scriptLoadedRef.current) return Promise.resolve();

    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = '/onlyoffice/v9/web-apps/apps/api/documents/api.js';
      script.onload = () => {
        scriptLoadedRef.current = true;
        resolve();
      };
      script.onerror = () => reject(new Error('Failed to load OnlyOffice API'));
      document.head.appendChild(script);
    });
  }, []);

  /**
   * Upload encrypted content to S3.
   */
  const uploadEncrypted = useCallback(
    async (
      content: ArrayBuffer,
      _format: string,
      epochMs: number,
    ): Promise<void> => {
      const vaultClient = window.__driveVaultClient;
      if (!vaultClient) {
        throw new Error('Vault client not available');
      }

      // Get key chain for encryption
      const driver = getDriver();
      const keyChain = await driver.getKeyChain(item.id);

      const entryKeyBinary = atob(keyChain.encrypted_key_for_user);
      const entryKeyBytes = new Uint8Array(entryKeyBinary.length);
      for (let i = 0; i < entryKeyBinary.length; i++) {
        entryKeyBytes[i] = entryKeyBinary.charCodeAt(i);
      }

      const encryptedKeyChain = keyChain.chain.map(entry => {
        const binary = atob(entry.encrypted_symmetric_key);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
      });

      // Encrypt via vault. The vault worker takes ownership of every buffer
      // passed through postMessage (transfer list), so hand it fresh copies
      // of the key material — otherwise the canonical keys held by the
      // relay / init closure get detached and subsequent encrypt/decrypt
      // calls fail with "wrong secret key for the given ciphertext".
      const { encryptedData } = await vaultClient.encryptWithKey(
        content,
        entryKeyBytes.buffer.slice(0),
        encryptedKeyChain.length > 0
          ? encryptedKeyChain.map(k => k.slice(0))
          : undefined
      );

      // Get a presigned S3 upload URL for the existing file key
      // S3 versioning keeps previous versions — no new filename needed
      const urlResponse = await fetchAPI(
        `items/${item.id}/encryption-upload-url/`,
        {
          method: 'POST',
          body: JSON.stringify({ epoch_ms: epochMs }),
          headers: { 'Content-Type': 'application/json' },
        },
        { redirectOn40x: false },
      );
      const {
        upload_url: uploadUrl,
        required_headers: requiredHeaders = {},
      } = await urlResponse.json();

      // Upload encrypted content to S3 via presigned URL (XHR like regular Drive uploads)
      const encryptedBytes = new Uint8Array(encryptedData);
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', uploadUrl);
        xhr.setRequestHeader('X-amz-acl', 'private');
        xhr.setRequestHeader('Content-Type', 'application/octet-stream');
        // Every header that was bound into the presigned signature MUST
        // be sent verbatim or S3 returns SignatureDoesNotMatch.
        for (const [name, value] of Object.entries(
          requiredHeaders as Record<string, string>,
        )) {
          xhr.setRequestHeader(name, value);
        }
        xhr.addEventListener('error', () => reject(new Error('S3 upload network error')));
        xhr.addEventListener('abort', () => reject(new Error('S3 upload aborted')));
        xhr.addEventListener('readystatechange', () => {
          if (xhr.readyState === 4) {
            if (xhr.status === 200) {
              resolve();
            } else {
              reject(new Error(`S3 upload failed: ${xhr.status} — ${xhr.responseText.slice(0, 200)}`));
            }
          }
        });
        xhr.send(encryptedBytes);
      });

      // Tell the relay this epoch is now durable in S3 — it will schedule
      // a delayed purge of older history entries after the grace window.
      relayRef.current?.sendSaveCommitted(epochMs);
    },
    [item.id]
  );

  /**
   * Main initialization: decrypt → convert → load editor.
   */
  useEffect(() => {
    let cancelled = false;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // Only the save leader is responsible for persisting state —
      // non-leader peers have no obligation to save, so closing
      // their tab loses nothing that wouldn't be re-requested from
      // the relay next time someone opens the doc. Suppressing the
      // browser confirm on non-leaders avoids the misleading
      // "unsaved changes" prompt when it's not true for this tab.
      if (isSaveLeaderRef.current() && hasUnsavedChanges()) {
        e.preventDefault();
      }
    };
    const handleVisibilityChange = () => {
      if (
        document.visibilityState === 'hidden' &&
        isSaveLeaderRef.current() &&
        hasUnsavedChanges()
      ) {
        forceSave().catch(() => {});
      }
    };

    // Global uncaught-error listener for OO crashes. The shield around
    // `Apply_Data` catches most collaborative-edit errors, but some
    // escape via the post-apply recalc path (e.g. `Refresh_RecalcData2
    // is not a function`). When that happens, the editor becomes
    // non-functional — we surface a recovery overlay so the user can
    // hard-reload and pick up the latest saved state.
    const isOOCrash = (src: string | undefined, msg: string): boolean => {
      // Any uncaught error whose source is inside the OO sdkjs
      // bundles is treated as a crash. Rationale: by the time a
      // sdkjs function throws past its caller, OO's internal state
      // is in an undefined condition. Whitelisting specific function
      // names lets future unknown failure modes silently corrupt
      // the editor. Known-benign cases (spell-check worker race,
      // collab cursor on missing run, paragraph lock on replaced
      // object) are caught and neutralised by explicit wrappers
      // upstream, so they never reach this listener.
      if (src && /\/sdkjs\/|sdk-all/.test(src)) return true;
      // Fallback: also match stacks whose message mentions sdkjs
      // symbols but whose `filename` was lost (cross-frame rethrow).
      return /sdk-all|\bAsc(?:Common|Format|Word)\b|CDocument\.|CCollaborative/.test(
        msg,
      );
    };
    const handleOOError = (event: ErrorEvent) => {
      if (cancelled) return;
      const src = event.filename ?? '';
      const msg = String(event.error?.stack ?? event.message ?? '');
      if (!isOOCrash(src, msg)) return;
      console.error('[OOEditor] uncaught OO crash — showing recovery', {
        src,
        msg,
      });
      enterCrashState();
    };
    window.addEventListener('error', handleOOError);

    const init = async () => {
      try {
        if (!item.url || !user) return;

        // Reset per-session refs. React doesn't unmount the component
        // on reinitKey bump — the effect just re-runs — so every ref
        // created with `useRef` still holds whatever value it had at
        // cleanup. Without this reset, the new session runs against
        // stale state from the previous one (dead editor instance,
        // pre-delay already "expired", old iframe window, etc.) and
        // inbound events end up going nowhere.
        console.warn(
          '[OOEditor] init() session reset — clearing refs, unsilencing outbound',
        );
        documentReadyRef.current = false;
        innerWindowRef.current = null;
        pendingRemoteChangesRef.current = [];
        replayBufferRef.current = [];
        replayPreDelayActiveRef.current = true;
        outgoingSilencedRef.current = false;
        recoveryResolveRef.current = null;
        setRecoveryWaiting(false);
        setEditorInstance(null);

        // Step 1: Load OnlyOffice script
        setState('loading');
        await loadOOScript();
        if (cancelled) return;

        // Step 2: Download and decrypt the file
        setState('decrypting');
        const driver = getDriver();
        const keyChain = await driver.getKeyChain(item.id);

        const itemUrl = item.url!;
        const response = await fetch(itemUrl, {
          credentials: 'include',
          cache: 'no-store',
        });
        if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
        // Read the snapshot epoch written at save time. Requires nginx to
        // forward the upstream S3 `x-amz-meta-epoch` header to the browser.
        // Missing (pre-epoch file) → 0 = "no snapshot anchor, replay all".
        const rawEpoch = response.headers.get('x-amz-meta-epoch');
        const snapshotEpochMs = rawEpoch ? Number(rawEpoch) : 0;
        const encryptedBuffer = await response.arrayBuffer();

        const vaultClient = window.__driveVaultClient;
        if (!vaultClient) throw new Error('Vault client not initialized');

        // Decrypt
        const entryKeyBinary = atob(keyChain.encrypted_key_for_user);
        const entryKeyBytes = new Uint8Array(entryKeyBinary.length);
        for (let i = 0; i < entryKeyBinary.length; i++) {
          entryKeyBytes[i] = entryKeyBinary.charCodeAt(i);
        }

        const encryptedKeyChain = keyChain.chain.map(entry => {
          const binary = atob(entry.encrypted_symmetric_key);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          return bytes.buffer;
        });

        // Clone the key material — the vault worker transfers its inputs,
        // detaching the originals. We still need these buffers intact for
        // the EncryptedRelay constructor below.
        const { data: decryptedBuffer } = await vaultClient.decryptWithKey(
          encryptedBuffer,
          entryKeyBytes.buffer.slice(0),
          encryptedKeyChain.length > 0
            ? encryptedKeyChain.map(k => k.slice(0))
            : undefined
        );
        if (cancelled) return;

        // Step 3: Convert to .bin format
        setState('converting');
        const { bin, images: extractedImages } = await convertToInternal(
          decryptedBuffer,
          filename,
        );
        if (cancelled) return;

        // Step 4: Create blob URL and load editor
        const blob = new Blob([bin], {
          type: 'application/octet-stream',
        });
        const blobUrl = URL.createObjectURL(blob);

        // Initialize participant tracking
        // Use user.sub (OIDC subject) — same ID the relay server uses
        const localUser = initLocalUser(user.sub!, user.full_name || user.email);
        const uniqueOOId = getUniqueOOId();
        resetPatchIndex(0);

        // Create the editor config
        // IMPORTANT: user.id must match the uniqueOOId used in lock responses,
        // otherwise OnlyOffice treats our own locks as belonging to another user
        const config: OOConfig = {
          document: {
            fileType: ooFileType,
            key: item.id + '_' + Date.now(),
            title: item.title,
            url: blobUrl,
          },
          documentType: docType,
          editorConfig: {
            mode: 'edit',
            user: {
              id: uniqueOOId,
              name: user.full_name || user.email,
            },
            lang: user.language || 'en',
            customization: {
              compactToolbar: false,
              forcesave: true,
              autosave: true,
              macros: false,
              plugins: false,
              help: false,
            } as any,
            permissions: {
              edit: true,
              comment: true,
              review: true,
              deleteCommentAuthorOnly: false,
              editCommentAuthorOnly: false,
              chat: false,
              macros: 'none',
              protect: false,
              modifyContentControl: false,
              fillForms: false,
            } as any,
          },
          events: {
            onAppReady: () => {
              // Register the images extracted by convertToInternal in OO's
              // g_oDocumentUrls registry BEFORE the document loads. OO walks
              // the .bin during loading and resolves image references via
              // g_oDocumentUrls.getImageUrl(name). Without these entries, OO
              // falls back to fetching `<name>` from a relative URL → 404.
              try {
                const ooIframe = document.querySelector(
                  'iframe[name="frameEditor"]',
                ) as HTMLIFrameElement | null;
                const innerWindow = ooIframe?.contentWindow as any;
                const docUrls = innerWindow?.AscCommon?.g_oDocumentUrls;
                if (docUrls && extractedImages.length > 0) {
                  for (const img of extractedImages) {
                    try {
                      // Use data URLs (not blob URLs) for portability:
                      // OO's clipboard binary embeds the image src verbatim,
                      // so a blob URL from this tab would fail to resolve
                      // when the same image is copy/pasted into another tab
                      // / user. Data URLs are self-contained and work
                      // anywhere getFullImageSrc2 sees a `data:` prefix.
                      const ext =
                        (img.name.split('.').pop() || 'png').toLowerCase();
                      const mime =
                        ext === 'jpg' || ext === 'jpeg'
                          ? 'image/jpeg'
                          : ext === 'gif'
                            ? 'image/gif'
                            : ext === 'svg'
                              ? 'image/svg+xml'
                              : ext === 'webp'
                                ? 'image/webp'
                                : 'image/png';
                      let binary = '';
                      const chunkSize = 0x8000;
                      for (
                        let offset = 0;
                        offset < img.data.byteLength;
                        offset += chunkSize
                      ) {
                        binary += String.fromCharCode.apply(
                          null,
                          Array.from(
                            img.data.subarray(
                              offset,
                              offset + chunkSize,
                            ),
                          ),
                        );
                      }
                      const dataUrl = `data:${mime};base64,${btoa(binary)}`;
                      docUrls.addImageUrl(img.name, dataUrl);
                    } catch (e) {
                      console.warn(
                        '[OOEditor] failed to register image',
                        img.name,
                        e,
                      );
                    }
                  }
                  console.log(
                    '[OOEditor] registered',
                    extractedImages.length,
                    'images in g_oDocumentUrls',
                  );
                }

                // Also register any media that arrived inline with the
                // history replay (images pasted by peers before we joined).
                // Without this, references in the replayed saveChanges
                // would 404 on the next image load cycle.
                if (docUrls) {
                  for (const [name, url] of Object.entries(
                    historyInitialMedia,
                  )) {
                    try {
                      docUrls.addImageUrl(name, url);
                    } catch (e) {
                      console.warn(
                        '[OOEditor] failed to register history media',
                        name,
                        e,
                      );
                    }
                  }
                }
              } catch (e) {
                console.warn('[OOEditor] image registration failed', e);
              }
            },
            onDocumentReady: () => {
              setState('ready');
              documentReadyRef.current = true;
              // The live saveChanges drain must NOT run inside
              // onDocumentReady — at that point OO has finished opening the
              // document but hasn't yet armed its auto-save interval in
              // `onDocumentContentReady`, and pushing external changes
              // straight into Continue_FastCollaborativeEditing lands on a
              // half-initialised object graph (observed as
              // `Run.GetDocumentPositionFromObject is not a function` and
              // friends).
              //
              // Hook the inner editor's onDocumentContentReady so the drain
              // fires AFTER OO's content-ready pipeline has completed and
              // the auto-save loop is live. If the hook can't be installed
              // (or content-ready has already fired), fall back to a
              // short setTimeout which usually pushes us past the race.
              let drained = false;
              const safeDrain = () => {
                if (drained) return;
                drained = true;
                try {
                  releaseReplayAfterPreDelay();
                } catch (e) {
                  console.warn('[OOEditor] deferred replay release failed', e);
                }
              };
              try {
                const ooIframe = document.querySelector(
                  'iframe[name="frameEditor"]',
                ) as HTMLIFrameElement | null;
                const innerWindow = ooIframe?.contentWindow as any;
                const innerEditor =
                  innerWindow?.editor || innerWindow?.editorCell;
                if (
                  innerEditor &&
                  typeof innerEditor.onDocumentContentReady === 'function' &&
                  !innerEditor.__driveContentReadyHooked
                ) {
                  innerEditor.__driveContentReadyHooked = true;
                  const orig = innerEditor.onDocumentContentReady.bind(
                    innerEditor,
                  );
                  innerEditor.onDocumentContentReady = function (
                    ...args: unknown[]
                  ) {
                    const result = orig(...args);
                    safeDrain();
                    return result;
                  };
                } else {
                  // Hook unavailable — defer to the next macrotask. In
                  // practice this fires after OO's internal
                  // onDocumentContentReady because that path runs
                  // synchronously inside the current call stack.
                  setTimeout(safeDrain, 0);
                }
              } catch (e) {
                console.warn('[OOEditor] content-ready hook failed', e);
                setTimeout(safeDrain, 0);
              }
              // Last-resort safety net: no matter what, drain within 500ms
              // so pending changes can't sit forever if our hook misses.
              setTimeout(safeDrain, 500);
              try {
                const ooIframe = document.querySelector(
                  'iframe[name="frameEditor"]',
                ) as HTMLIFrameElement | null;
                const innerWindow = ooIframe?.contentWindow as any;
                innerWindowRef.current = innerWindow;

                // Install the OO-crash error listener INSIDE the iframe
                // too — uncaught errors from sdk-all.js fire on the
                // iframe's window, not the top-level one, so our outer
                // listener never sees them.
                if (innerWindow && !innerWindow.__driveCrashHooked) {
                  innerWindow.__driveCrashHooked = true;
                  innerWindow.addEventListener('error', (evt: ErrorEvent) => {
                    handleOOError(evt);
                  });
                  innerWindow.addEventListener(
                    'unhandledrejection',
                    (evt: PromiseRejectionEvent) => {
                      const msg = String(
                        evt.reason?.stack ?? evt.reason ?? '',
                      );
                      handleOOError({
                        filename: '',
                        message: msg,
                        error: evt.reason,
                      } as ErrorEvent);
                    },
                  );
                }

                // Pre-create OO's clipboard sanitization iframe with a
                // permissive sandbox. OO's CommonIframe_PasteStart sets
                // sandbox="allow-same-origin" (no allow-scripts), which
                // Chrome warns about and which breaks Cmd+V image paste.
                // By creating the element first under the same id, OO's
                // `if(!ifr)` check finds ours and skips its own creation.
                const cb = innerWindow?.AscCommon?.g_clipboardBase;
                if (cb && !innerWindow.document.getElementById(cb.CommonIframeId)) {
                  const pasteIfr = innerWindow.document.createElement('iframe');
                  pasteIfr.name = cb.CommonIframeId;
                  pasteIfr.id = cb.CommonIframeId;
                  pasteIfr.style.position = 'absolute';
                  pasteIfr.style.top = '-100px';
                  pasteIfr.style.left = '0px';
                  pasteIfr.style.width = '10000px';
                  pasteIfr.style.height = '100px';
                  pasteIfr.style.overflow = 'hidden';
                  pasteIfr.style.zIndex = '-1000';
                  pasteIfr.setAttribute(
                    'sandbox',
                    'allow-same-origin allow-scripts',
                  );
                  innerWindow.document.body.appendChild(pasteIfr);
                  cb.CommonIframe = pasteIfr;
                }

                // Override AscCommon.sendImgUrls — OO calls this from the
                // paste path to "upload" image URLs to the document server
                // (POST /downloadas/?c=imgurls) and get back local media
                // paths. Without a DS, that hangs the "Loading image" modal
                // forever. Register each URL synchronously in g_oDocumentUrls
                // and return immediately.
                if (innerWindow?.AscCommon && !innerWindow.AscCommon.__driveImgUrlsPatched) {
                  let imgCounter = 0;
                  innerWindow.AscCommon.sendImgUrls = function (
                    api: any,
                    images: any[],
                    callback: (data: Array<{ url: string; path: string }>) => void,
                  ) {
                    if (!api.isOpenedFrameEditor) {
                      api.sync_StartAction?.(
                        innerWindow.Asc?.c_oAscAsyncActionType?.BlockInteraction ?? 1,
                        innerWindow.Asc?.c_oAscAsyncAction?.LoadImage ?? 0,
                      );
                    }
                    const out: Array<{ url: string; path: string }> = [];
                    const urls: Record<string, string> = {};
                    for (const src of images) {
                      if (typeof src !== 'string') {
                        out.push({ url: 'error', path: 'error' });
                        continue;
                      }
                      // Detect extension from the data URL mime, default png.
                      const mimeMatch = /^data:image\/([a-z0-9+]+)/.exec(src);
                      const ext = mimeMatch ? mimeMatch[1].replace('+xml', '') : 'png';
                      imgCounter += 1;
                      const name = `image_${Date.now()}_${imgCounter}.${ext}`;
                      const path = 'media/' + name;
                      urls[path] = src;
                      out.push({ url: src, path });
                      // Stash the bytes so they ride out with the next
                      // saveChanges envelope to peers — otherwise remote
                      // users see the synthetic image name but have no
                      // bytes to render and 404 on the bare filename.
                      relayRef.current?.queuePendingMedia(name, src);
                    }
                    innerWindow.AscCommon.g_oDocumentUrls.addUrls(urls);
                    if (!api.isOpenedFrameEditor) {
                      api.sync_EndAction?.(
                        innerWindow.Asc?.c_oAscAsyncActionType?.BlockInteraction ?? 1,
                        innerWindow.Asc?.c_oAscAsyncAction?.LoadImage ?? 0,
                      );
                    }
                    callback(out);
                  };
                  innerWindow.AscCommon.__driveImgUrlsPatched = true;
                }

                const innerEditor = innerWindow?.editor || innerWindow?.editorCell;
                // NOTE: we no longer monkey-patch any sdkjs prototype
                // method (Update_ForeignCursor, CGraphicObjects.*,
                // SpellCheck_CallBack, private_LockByMe, etc.). Those
                // wrappers were fragile — each one tied us to specific
                // internal paths that break on OO upgrades and leave
                // us silently catching errors we didn't anticipate.
                // The uniform rule is now: any uncaught error from
                // sdkjs triggers the `oo-crashed` overlay via the
                // iframe-level `error` listener, and the user reloads
                // to pick up the last saved state.

                // REMOVED: apply-drop verifier based on
                // `CoHistory.GetChangeCount()`. The counter is
                // incremented only on OUTGOING (own) change saves
                // via `AddOwnChanges` / `private_AddOverallChange`;
                // it is never touched for applied remote changes.
                // Measuring remote applies against it produced false
                // positives that silenced outbound traffic on
                // healthy sessions and broke the reload flow. If a
                // better signal appears later we can reinstate a
                // verification here — for now we rely on uncaught
                // errors inside the apply pipeline to flip the
                // crash overlay via the iframe error listener.

                // CCollaborativeChanges.Apply_Data is INTENTIONALLY not
                // shielded. When a change fails to apply, the document
                // state becomes inconsistent — silently swallowing it
                // lets OO keep processing subsequent changes on top of
                // a corrupt graph, which diverges peers invisibly. We
                // let the error propagate so OO's batch loop bails,
                // and our iframe-level `error` listener catches the
                // uncaught exception and flips the editor to the
                // `oo-crashed` state with the reload overlay.

                if (innerEditor) {
                  let proto = Object.getPrototypeOf(innerEditor);
                  while (
                    proto &&
                    !Object.prototype.hasOwnProperty.call(
                      proto,
                      '_downloadAsUsingServer',
                    )
                  ) {
                    proto = Object.getPrototypeOf(proto);
                  }
                  if (proto && !proto.__driveDownloadPatched) {
                    const original = proto._downloadAsUsingServer;
                    proto._downloadAsUsingServer = function (
                      _actionType: unknown,
                      _options: unknown,
                      oAdditionalData: any,
                      _dataContainer: unknown,
                      downloadType: unknown,
                    ) {
                      (window as any).__driveDownloadCtx = {
                        title: oAdditionalData?.title,
                        outputformat: oAdditionalData?.outputformat,
                        downloadType,
                      };
                      // eslint-disable-next-line prefer-rest-params
                      return original.apply(this, arguments as any);
                    };
                    proto.__driveDownloadPatched = true;
                  }
                }
              } catch (e) {
                console.warn('[OOEditor] failed to patch download flow', e);
              }
            },
            onError: (event: { data: unknown }) => {
              console.error('OnlyOffice error:', event.data);
              setError(String(event.data));
              setState('error');
            },
          } as any,
        };

        if (!window.DocsAPI) {
          throw new Error('OnlyOffice API not loaded');
        }

        // OnlyOffice's connectMockServer expects window.APP to exist.
        // We also install a `getUserColor(userId)` hook that OO's
        // _getUserColorById checks before its internal cache. Without this,
        // cursor and participant-list calls hit different cache keys (cursor
        // passes null for userName, panel passes the username) and the same
        // user ends up with two different colors. Returning a deterministic
        // color per id keeps both call sites in sync.
        (window as any).APP = (window as any).APP || {};
        // Image insertion: OO calls window.parent.APP.UploadImageFiles when
        // the user drops/pastes an image. With a real DocumentServer it'd
        // POST the bytes and return URLs from the server. For E2E we never
        // touch the network — we encode each file as a data: URL and hand it
        // back. OO embeds the data URL directly into the document model, so
        // it travels inside the saveChanges envelope to peers (no side
        // channel needed) and OO reads the bytes back at save time to
        // serialize them into the .bin / .odt as real binary.
        //
        // Hard size cap: an image is base64-encoded into the change record
        // and ships through the encrypted relay, which itself caps payload
        // size. Reject up front with OO's own UplImageSize error (-9) so OO
        // shows its native "image too large" toast.
        const MAX_IMAGE_BYTES = 50 * 1024 * 1024;
        const ASC_ERR_UPL_IMAGE_SIZE = -9;

        // Convert image files into data: URLs ready to hand back to OO.
        // Enforces the per-file size cap and rejects with the size-error
        // sentinel so callers can return OO's own UplImageSize toast.
        const filesToDataURLs = async (
          files: FileList | File[],
        ): Promise<string[]> => {
          const arr = Array.from(files);
          for (const f of arr) {
            if (f.size > MAX_IMAGE_BYTES) {
              throw ASC_ERR_UPL_IMAGE_SIZE;
            }
          }
          return Promise.all(
            arr.map(
              file =>
                new Promise<string>((resolve, reject) => {
                  const reader = new FileReader();
                  reader.onload = () => resolve(reader.result as string);
                  reader.onerror = () =>
                    reject(reader.error ?? new Error('FileReader failed'));
                  reader.readAsDataURL(file);
                }),
            ),
          );
        };

        // Drag-and-drop / paste path.
        (window as any).APP.UploadImageFiles = (
          files: FileList | File[],
          _documentId: string,
          _documentUserId: string,
          _jwt: string,
          callback: (err: number | null, urls: string[]) => void,
        ) => {
          filesToDataURLs(files)
            .then(urls => callback(null, urls))
            .catch(err => {
              if (err !== ASC_ERR_UPL_IMAGE_SIZE) {
                console.error('[OOEditor] UploadImageFiles failed', err);
              }
              callback(ASC_ERR_UPL_IMAGE_SIZE, []);
            });
        };

        // Print / Print Selection / Save-as ANY format.
        // OO routes ALL these through the same `printPdf` hook because our
        // download type is None (no real Document Server). We branch on the
        // target format captured by the _downloadAsUsingServer patch above:
        //   - PDF   → dual-input bin → pdf via convertFromInternalToPdf
        //   - other → asc_nativeGetFile + convertFromInternal(target ext)
        // Then we trigger a download (or hand the URL to OO for print).
        const MIME_BY_EXT: Record<string, string> = {
          pdf: 'application/pdf',
          docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          doc: 'application/msword',
          odt: 'application/vnd.oasis.opendocument.text',
          rtf: 'application/rtf',
          txt: 'text/plain',
          html: 'text/html',
          xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          xls: 'application/vnd.ms-excel',
          ods: 'application/vnd.oasis.opendocument.spreadsheet',
          csv: 'text/csv',
          pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
          ppt: 'application/vnd.ms-powerpoint',
          odp: 'application/vnd.oasis.opendocument.presentation',
        };

        (window as any).APP.printPdf = (
          dataContainer: { data: Uint8Array | ArrayBuffer | null },
          callback: (result: unknown) => void,
        ) => {
          (async () => {
            try {
              const ooIframe = document.querySelector(
                'iframe[name="frameEditor"]',
              ) as HTMLIFrameElement | null;
              const innerWindow = ooIframe?.contentWindow as any;
              const innerEditor =
                innerWindow?.editor || innerWindow?.editorCell;
              if (!innerEditor?.asc_nativeGetFile) {
                throw new Error('inner editor not ready');
              }
              const rawBin = innerEditor.asc_nativeGetFile();
              if (!rawBin) {
                throw new Error('empty document');
              }
              let binBuffer: ArrayBuffer;
              if (typeof rawBin === 'string') {
                binBuffer = new TextEncoder().encode(rawBin)
                  .buffer as ArrayBuffer;
              } else if (rawBin instanceof ArrayBuffer) {
                binBuffer = rawBin;
              } else {
                binBuffer = rawBin.buffer;
              }

              const ctx = (window as any).__driveDownloadCtx ?? {};
              const title: string = ctx.title || `document.${x2tExtension}`;
              const ext = (title.split('.').pop() || x2tExtension).toLowerCase();
              const isPrint = ctx.downloadType === 'asc_onPrintUrl';

              let outBytes: Uint8Array<ArrayBuffer>;
              const mime = MIME_BY_EXT[ext] || 'application/octet-stream';

              if (ext === 'pdf') {
                const rawLayout = dataContainer?.data;
                if (!rawLayout) {
                  throw new Error('missing PDF layout bin (dataContainer.data)');
                }
                const layoutBuffer: ArrayBuffer =
                  rawLayout instanceof ArrayBuffer
                    ? rawLayout
                    : (rawLayout.buffer.slice(
                        rawLayout.byteOffset,
                        rawLayout.byteOffset + rawLayout.byteLength,
                      ) as ArrayBuffer);
                // Gather every image registered in OO's document urls so
                // the PDF writer can find them in /working/media/. Without
                // this, Print Selection (and any path that goes through OO's
                // selection renderer) silently drops images.
                const media = new Map<string, Uint8Array>();
                try {
                  const urls =
                    innerWindow?.AscCommon?.g_oDocumentUrls?.getUrls?.() ?? {};
                  console.log(
                    '[OOEditor] g_oDocumentUrls keys:',
                    Object.keys(urls),
                  );
                  // Also peek at OO's image cache — that's where inserted
                  // images actually live when they were passed as data URLs.
                  const imgCache =
                    innerWindow?.Asc?.editor?.ImageLoader?.map_image_index;
                  if (imgCache) {
                    console.log(
                      '[OOEditor] image cache keys:',
                      Object.keys(imgCache).map(k =>
                        k.length > 80 ? k.slice(0, 80) + '…' : k,
                      ),
                    );
                  }
                  await Promise.all(
                    Object.entries(urls).map(async ([key, value]) => {
                      if (typeof value !== 'string') return;
                      try {
                        const resp = await fetch(value);
                        if (!resp.ok) return;
                        const bytes = new Uint8Array(await resp.arrayBuffer());
                        // x2t expects images at /working/media/<name>. If the
                        // key already starts with "media/" we strip it; if
                        // not, we keep the key as the filename.
                        const name = key.startsWith('media/')
                          ? key.slice('media/'.length)
                          : key;
                        media.set(name, bytes);
                      } catch (e) {
                        console.warn(
                          '[OOEditor] failed to fetch image',
                          key,
                          e,
                        );
                      }
                    }),
                  );
                  console.log(
                    '[OOEditor] media files written to /working/media/:',
                    Array.from(media.keys()),
                  );
                } catch (e) {
                  console.warn('[OOEditor] image gather failed', e);
                }
                console.log(
                  '[OOEditor] PDF layout (dataContainer.data) size:',
                  layoutBuffer.byteLength,
                );
                outBytes = await convertFromInternalToPdf(
                  binBuffer,
                  layoutBuffer,
                  media,
                );
              } else {
                const docType =
                  EXTENSION_TO_X2T_TYPE[ext] || x2tType || 'doc';
                outBytes = await convertFromInternal(
                  binBuffer,
                  ext,
                  docType,
                );
              }

              const blob = new Blob([outBytes], { type: mime });
              const url = URL.createObjectURL(blob);

              if (isPrint) {
                // Hidden iframe in the PARENT window opens the PDF and we
                // call contentWindow.print() once it loads. This shows
                // Chrome's top-level Print dialog. Doing it inside OO's
                // sandboxed iframe crashes the nested PDF viewer.
                const old = document.getElementById('drive-print-iframe');
                if (old) old.remove();
                const iframe = document.createElement('iframe');
                iframe.id = 'drive-print-iframe';
                iframe.style.position = 'fixed';
                iframe.style.right = '0';
                iframe.style.bottom = '0';
                iframe.style.width = '0';
                iframe.style.height = '0';
                iframe.style.border = '0';
                iframe.onload = () => {
                  try {
                    iframe.contentWindow?.focus();
                    iframe.contentWindow?.print();
                  } catch (e) {
                    console.error('[OOEditor] print failed, opening tab', e);
                    window.open(url, '_blank');
                  }
                };
                iframe.src = url;
                document.body.appendChild(iframe);
              } else {
                const a = document.createElement('a');
                a.href = url;
                a.download = title;
                a.rel = 'noopener';
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              }

              // Tell OO we're done. Passing null short-circuits its
              // processSavedFile path so it doesn't try to fire its own
              // download/print on top of ours.
              callback(null);
            } catch (err) {
              console.error('[OOEditor] printPdf failed', err);
              callback(null);
            }
          })();
        };

        // Modal "Insert image / Replace image / From file" path: opens a
        // file picker and forwards the result through the same converter.
        (window as any).APP.AddImage = (
          successCb: (res: { url: string; name: string }) => void,
          errorCb?: (err?: unknown) => void,
        ) => {
          const input = document.createElement('input');
          input.type = 'file';
          input.accept = 'image/*';
          input.style.display = 'none';
          input.addEventListener('change', () => {
            const file = input.files?.[0];
            document.body.removeChild(input);
            if (!file) {
              errorCb?.();
              return;
            }
            filesToDataURLs([file])
              .then(([url]) => successCb({ url, name: file.name }))
              .catch(err => errorCb?.(err));
          });
          document.body.appendChild(input);
          input.click();
        };

        (window as any).APP.getUserColor = (userId: string) => {
          if (!userId) return null;
          // 16 colors evenly distributed on the HSL wheel — same id → same color.
          let hash = 0;
          for (let i = 0; i < userId.length; i++) {
            hash = (hash * 31 + userId.charCodeAt(i)) >>> 0;
          }
          const palette = [
            { r: 0xea, g: 0x44, b: 0x35 }, // red
            { r: 0xfb, g: 0x8c, b: 0x00 }, // orange
            { r: 0xfd, g: 0xd8, b: 0x35 }, // yellow
            { r: 0x7c, g: 0xb3, b: 0x42 }, // light green
            { r: 0x2e, g: 0x7d, b: 0x32 }, // green
            { r: 0x00, g: 0xac, b: 0xc1 }, // cyan
            { r: 0x16, g: 0x68, b: 0xdd }, // blue
            { r: 0x3f, g: 0x51, b: 0xb5 }, // indigo
            { r: 0x7e, g: 0x57, b: 0xc2 }, // violet
            { r: 0xab, g: 0x47, b: 0xbc }, // purple
            { r: 0xec, g: 0x40, b: 0x7a }, // pink
            { r: 0x8d, g: 0x6e, b: 0x63 }, // brown
            { r: 0x55, g: 0x6c, b: 0x78 }, // slate
            { r: 0x00, g: 0x69, b: 0x7c }, // teal
            { r: 0xc6, g: 0x28, b: 0x28 }, // dark red
            { r: 0x37, g: 0x47, b: 0x4f }, // gunmetal
          ];
          const c = palette[hash % palette.length];
          return { r: c.r, g: c.g, b: c.b, a: 255 };
        };

        // ----------------------------------------------------------------
        // Relay-first init: connect the encrypted relay BEFORE constructing
        // OO. Any saveChanges envelopes replayed by the relay as part of
        // the room history are unpacked into `historyInitialChanges` and
        // fed to OO via `getInitialChanges()` during its open flow — OO's
        // proper channel for pre-load collaborative changes. This avoids
        // the race where history replayed through `sendMessageToOO` after
        // onDocumentReady hits OO's auto-save interval with an object
        // graph that isn't fully initialised yet.
        //
        // Live cursor/meta/message events that happen to arrive during
        // the history window are ignored at the OO layer (editor isn't
        // mounted yet — sendToEditor is a no-op) but their side effects
        // on peer-tracking refs still apply.
        // ----------------------------------------------------------------
        const historyInitialMedia: Record<string, string> = {};
        let historyPhaseComplete = false;
        let resolveHistoryReady: () => void = () => {};
        const historyReadyPromise = new Promise<void>(resolve => {
          resolveHistoryReady = resolve;
        });
        const endPreloadPhase = () => {
          if (historyPhaseComplete) return;
          historyPhaseComplete = true;
          console.log(
            '[OOEditor] preload phase complete —',
            replayBufferRef.current.length,
            'saveChanges buffered,',
            pendingRemoteChangesRef.current.length,
            'ancillary events queued,',
            Object.keys(historyInitialMedia).length,
            'media items',
          );
          resolveHistoryReady();
        };

        try {
          const relay = new EncryptedRelay({
            roomId: item.id,
            userId: user.sub!,
            userName: user.full_name || user.email,
            vaultClient,
            encryptedSymmetricKey: entryKeyBytes.buffer,
            encryptedKeyChain:
              encryptedKeyChain.length > 0 ? encryptedKeyChain : [],
            sinceTimestampMs: Number.isFinite(snapshotEpochMs)
              ? snapshotEpochMs
              : 0,
            callbacks: {
              onSaveChanges: (_userId, message, media) => {
                // Media is accumulated the same way in both phases so it
                // ends up in g_oDocumentUrls before OO resolves references.
                if (media) {
                  if (!historyPhaseComplete) {
                    Object.assign(historyInitialMedia, media);
                  } else {
                    try {
                      const docUrls =
                        innerWindowRef.current?.AscCommon?.g_oDocumentUrls;
                      if (docUrls) {
                        for (const [name, url] of Object.entries(media)) {
                          docUrls.addImageUrl(name, url);
                        }
                      }
                    } catch (e) {
                      console.warn(
                        '[OOEditor] failed to register inbound media',
                        e,
                      );
                    }
                  }
                }

                // Preload and live phases now take the SAME path: queue
                // the change into pendingRemoteChangesRef if the editor
                // isn't ready yet, otherwise apply immediately. This
                // matches CryptPad's architecture — every inbound
                // saveChanges flows through `sendMessageToOO`, never
                // through OO's `getInitialChanges` channel (which
                // silently drops replay bursts in our testing).
                if (!historyPhaseComplete) {
                  try {
                    const changes = (message as { changes?: unknown })
                      .changes;
                    const n = Array.isArray(changes) ? changes.length : 0;
                    console.log(
                      `[HISTORY replay queued] changes=${n} ` +
                        `(snapshotEpochMs=${snapshotEpochMs})`,
                      message,
                    );
                  } catch {
                    /* ignore logging failures */
                  }
                }

                // Forward the envelope to OO unchanged, but observe
                // its `changesIndex` so our local `patchIndex` adopts
                // the sender's counter. When we later emit our own
                // outgoing `saveChanges`, `wrapOutgoingSaveChanges`
                // will continue numbering from there — matching OO's
                // internal state.
                const apply = () => {
                  observeIncomingSaveChanges(
                    message as Record<string, unknown>,
                  );
                  withIncomingOTGate(() =>
                    sendToEditorGuarded(message as any),
                  );
                };
                // All saveChanges flow through the index-gated reorder
                // buffer. While the editor is still mounting / during
                // the post-ready pre-delay, the buffer holds events
                // until `releaseReplayAfterPreDelay` flushes them in
                // strict changesIndex order.
                handleIncomingSaveChanges(
                  message as Record<string, unknown>,
                  apply,
                );
              },
              onHistoryEnd: () => {
                endPreloadPhase();
              },
              onPeerJoin: (userId, userName, peerCanEdit, joinedAt) => {
                if (peerCanEdit) {
                  const existing = editorPeersRef.current.get(userId);
                  // Keep the earliest joinedAt for a userId — if a
                  // second tab of the same user joins later, the
                  // original one still wins the leader tiebreak.
                  if (existing === undefined || joinedAt < existing) {
                    editorPeersRef.current.set(userId, joinedAt);
                  }
                }
                addRemoteUser(userId, userName, userId);
                sendToEditor(buildConnectStateMessage() as any);
              },
              onPeerLeave: userId => {
                editorPeersRef.current.delete(userId);
                removeRemoteUser(userId);
                releaseAllUserLocks(userId);
                sendToEditor(buildConnectStateMessage() as any);
              },
              onRoomState: peers => {
                editorPeersRef.current.clear();
                for (const peer of peers) {
                  if (peer.userId) {
                    if (peer.canEdit) {
                      const existing = editorPeersRef.current.get(peer.userId);
                      if (existing === undefined || peer.joinedAt < existing) {
                        editorPeersRef.current.set(peer.userId, peer.joinedAt);
                      }
                    }
                    addRemoteUser(peer.userId, peer.userName, peer.userId);
                  }
                }
                sendToEditor(buildConnectStateMessage() as any);
              },
              onLockUpdate: (type, userId, lockData) => {
                const lockId = JSON.stringify(lockData);
                if (type === 'acquire') {
                  acquireCellLock(lockId, userId, lockData);
                } else {
                  releaseCellLock(lockId, userId);
                }
                const apply = () =>
                  sendToEditor({
                    type: 'getLock',
                    locks: [lockData],
                  } as any);
                if (!documentReadyRef.current) {
                  pendingRemoteChangesRef.current.push(apply);
                  return;
                }
                apply();
              },
              onCursorUpdate: (userId, cursor) => {
                const senderOOId = getRemoteOOInternalId(userId);
                if (!senderOOId) return;
                const cursorString =
                  typeof cursor === 'string' ? cursor : JSON.stringify(cursor);
                const apply = () =>
                  sendToEditorGuarded({
                    type: 'cursor',
                    messages: [
                      {
                        cursor: cursorString,
                        user: senderOOId,
                        useridoriginal: senderOOId,
                        time: Date.now(),
                      },
                    ],
                  } as any);
                if (!documentReadyRef.current) {
                  pendingRemoteChangesRef.current.push(apply);
                  return;
                }
                apply();
              },
              onMessageBroadcast: (_userId, messages) => {
                const apply = () =>
                  sendToEditorGuarded({ type: 'message', messages } as any);
                if (!documentReadyRef.current) {
                  pendingRemoteChangesRef.current.push(apply);
                  return;
                }
                apply();
              },
              onMetaBroadcast: (_userId, messages) => {
                const apply = () =>
                  sendToEditorGuarded({ type: 'meta', messages } as any);
                if (!documentReadyRef.current) {
                  pendingRemoteChangesRef.current.push(apply);
                  return;
                }
                apply();
              },
              onSaveLock: () => {
                // Save coordination handled by leader election, not lock messages
              },
              onConnectionChange: connected => {
                setIsConnected(connected);
                if (connected) setRelayFailed(false);
              },
              onReconnectFailed: () => {
                setRelayFailed(true);
                // Unblock OO construction if we were still waiting.
                endPreloadPhase();
              },
              onStaleHistory: () => {
                // Relay told us our cursor is older than its purge
                // floor — we cannot catch up from memory. Tear the
                // editor down and re-run init from scratch so we
                // refetch the S3 snapshot and rebuild OO on top of it.
                console.warn(
                  '[OOEditor] stale history — triggering full reinit from S3',
                );
                setState('stale-resyncing');
                setReinitKey(k => k + 1);
              },
              onRemoteSaveCommitted: (epochMs, userId) => {
                // The leader just persisted a checkpoint that covers
                // the shared state we're holding. Clear our local
                // "unsaved" marker so beforeunload doesn't prompt on
                // close. Also advance our relay cursor past the epoch
                // to match what the relay itself will purge.
                console.log(
                  '[OOEditor] remote save committed by',
                  userId,
                  'epoch=',
                  epochMs,
                );
                markRemoteSaveCommitted();
                relayRef.current?.observeRemoteSaveCommitted(epochMs);
                // If the user clicked the crash-reload button and we
                // were waiting for a fresh save to land before
                // reinit, this is the signal — resolve the wait and
                // proceed with the reload.
                if (recoveryResolveRef.current) {
                  recoveryResolveRef.current();
                }
              },
              onPeerNeedsSave: peerUserId => {
                // A crashed peer is asking the save-leader to persist
                // so they can reload against a fresh snapshot epoch.
                // Only the leader acts; everyone else ignores it.
                // The leader's checkpointing layer has its own
                // `isSaving` guard so calling `forceSave()` multiple
                // times in quick succession is already safe.
                if (!isSaveLeaderRef.current()) return;
                if (outgoingSilencedRef.current) {
                  // If we're ourselves in crash state we can't save
                  // trustworthy content — let whoever else is around
                  // handle it, or let the requester fall through to
                  // the current epoch reload.
                  return;
                }
                console.log(
                  '[OOEditor] peer',
                  peerUserId,
                  'needs save — triggering forceSave as leader',
                );
                forceSave().catch(e => {
                  console.warn(
                    '[OOEditor] forceSave from peer request failed',
                    e,
                  );
                });
              },
            },
          });
          relayRef.current = relay;
          setState('syncing-history');
          relay.connect();
        } catch (relayErr) {
          console.warn('Relay setup failed (single-user mode):', relayErr);
          endPreloadPhase();
        }

        // Wait for the preload phase to complete. Outer safety net in case
        // the relay never fires any callback at all (e.g. connection stuck
        // in CONNECTING). A large history burst with inline images can
        // legitimately take a while to stream + decrypt, so this is
        // intentionally generous — the overlay keeps the editor locked
        // from user input while we wait.
        await Promise.race([
          historyReadyPromise,
          new Promise<void>(resolve =>
            setTimeout(() => {
              if (!historyPhaseComplete) {
                console.warn(
                  '[OOEditor] preload outer timeout — proceeding',
                );
                endPreloadPhase();
              }
              resolve();
            }, 120_000),
          ),
        ]);
        if (cancelled) return;

        // History replay is queued into `pendingRemoteChangesRef` above
        // and will be drained (paced) once OO fires `onDocumentContentReady`.
        // We do NOT use `setInitialChanges` / `getInitialChanges`: that
        // channel silently drops replay bursts in our testing. CryptPad's
        // architecture confirms the right path is `sendMessageToOO`.
        console.log(
          '[OOEditor:preload] ready to construct editor —',
          replayBufferRef.current.length,
          'saveChanges buffered,',
          pendingRemoteChangesRef.current.length,
          'ancillary events queued,',
          Object.keys(historyInitialMedia).length,
          'media items',
        );

        // Create the editor
        const editor = new window.DocsAPI.DocEditor(
          'oo-editor-placeholder',
          config
        );
        editorRef.current = editor;
        setEditorInstance(editor);

        // Connect our mock server (replaces Document Server)
        // This must happen before relay setup — editor needs to work standalone
        const callbacks = createMockServerCallbacks({
          docType,
          onSaveChangesBroadcast: message => {
            // A crashed editor must not leak its corrupt state to
            // peers — otherwise one broken tab takes down the whole
            // room when its autosave loop emits garbage that crashes
            // Apply_OtherChanges on every other client.
            if (outgoingSilencedRef.current) {
              console.warn(
                '[OOEditor] outgoing saveChanges suppressed (crash state)',
              );
              return;
            }
            // DIAGNOSTIC: dump every outbound saveChanges so we can
            // compare what user1 emits vs what user2 receives and tries
            // to apply in its history replay.
            try {
              const changes = (message as { changes?: unknown }).changes;
              const arr = Array.isArray(changes) ? changes : [];
              console.log(
                '[OOEditor:send] saveChanges',
                {
                  count: arr.length,
                  changes: arr.map((c, i) => {
                    const ooc = c as {
                      user?: string;
                      useridoriginal?: string;
                      change?: string;
                    };
                    const raw = ooc.change ?? '';
                    let parsed: unknown = raw;
                    try {
                      parsed = JSON.parse(raw);
                    } catch {
                      /* leave as string */
                    }
                    const preview =
                      typeof raw === 'string' && raw.length > 500
                        ? raw.slice(0, 500) + `…(+${raw.length - 500})`
                        : raw;
                    return {
                      index: i,
                      user: ooc.user,
                      useridoriginal: ooc.useridoriginal,
                      typeCode: Array.isArray(parsed)
                        ? (parsed as unknown[])[0]
                        : undefined,
                      parsed,
                      raw: preview,
                    };
                  }),
                },
              );
            } catch {
              /* ignore */
            }
            relayRef.current?.sendSaveChanges(message);
          },
          onLockRequest: (type, lockData) => {
            if (outgoingSilencedRef.current) return;
            relayRef.current?.sendLock(type, lockData);
          },
          onCursorUpdate: cursor => {
            if (outgoingSilencedRef.current) return;
            relayRef.current?.sendCursor(cursor);
          },
          onMessageBroadcast: messages => {
            if (outgoingSilencedRef.current) return;
            relayRef.current?.sendMessage(messages);
          },
          onMetaBroadcast: messages => {
            if (outgoingSilencedRef.current) return;
            relayRef.current?.sendMeta(messages);
          },
          onSaveLockCheck: () => false,
        });
        editor.connectMockServer(callbacks);

        // Initialize auto-save — readers don't save
        console.log(
          '[checkpoint] init gate — canEdit:',
          canEdit,
          'abilities:',
          item.abilities,
        );
        // Install the leader-election implementation into the ref so
        // both initCheckpointing and the beforeunload handler use the
        // same rule. The closure captures `canEdit` and `user` from
        // scope but reads the live peer map / relay joinedAt each
        // call, so it stays correct as peers join/leave.
        isSaveLeaderRef.current = () => {
          if (!canEdit) return false;
          const myId = user!.sub!;
          const myJoinedAt = relayRef.current?.joinedAt ?? 0;
          for (const [peerId, peerJoinedAt] of editorPeersRef.current) {
            if (peerId < myId) return false;
            if (peerId === myId && peerJoinedAt < myJoinedAt) return false;
          }
          return true;
        };
        if (canEdit) initCheckpointing({
          editor,
          format: x2tExtension,
          type: x2tType,
          userId: user.sub!,
          onUpload: uploadEncrypted,
          isSaveLeader: () => isSaveLeaderRef.current(),
        });

        // Listen for tab close/refresh to save or warn
        window.addEventListener('beforeunload', handleBeforeUnload);
        document.addEventListener('visibilitychange', handleVisibilityChange);

        // Don't revoke blob URL here — OnlyOffice fetches it asynchronously.
        // It will be cleaned up when the component unmounts.
      } catch (err) {
        if (!cancelled) {
          console.error('OOEditor init failed:', err);
          setError(
            err instanceof Error ? err.message : 'Failed to load editor'
          );
          setState('error');
        }
      }
    };

    init();

    return () => {
      cancelled = true;
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('error', handleOOError);
      stopCheckpointing();
      forceSave().catch(console.error);
      // Clean up locks and relay
      resetAllLocks();
      if (relayRef.current) {
        relayRef.current.destroy();
        relayRef.current = null;
      }
      if (editorRef.current) {
        try {
          editorRef.current.destroyEditor();
        } catch {
          // Editor may already be destroyed
        }
        editorRef.current = null;
      }
      // Clear the mock-server's editor reference so any in-flight
      // messages between here and the next init() don't land on the
      // destroyed instance.
      setEditorInstance(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id, reinitKey]);

  if (state === 'error') {
    const isNoKeysError =
      !!error && /no key pair|hasKeys|key pair found/i.test(error);
    const headline = isNoKeysError
      ? t(
          'explorer.encrypted.no_keys_headline',
          'Encryption keys required',
        )
      : t('explorer.encrypted.editor_error', 'Failed to load editor');
    const body = isNoKeysError
      ? t(
          'explorer.encrypted.no_keys_body',
          'You don\'t have an encryption key pair set up for your account yet. Generate or restore your encryption keys from your profile menu, then reopen this document.',
        )
      : error;

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          gap: '20px',
          padding: '32px',
          textAlign: 'center',
          maxWidth: '560px',
          margin: '0 auto',
        }}
      >
        <span
          className="material-icons"
          style={{
            fontSize: '56px',
            color: 'var(--c--theme--colors--danger-600)',
          }}
        >
          {isNoKeysError ? 'lock' : 'error'}
        </span>
        <h2
          style={{
            margin: 0,
            fontSize: '20px',
            fontWeight: 600,
            color: 'var(--c--theme--colors--greyscale-900, #111)',
          }}
        >
          {headline}
        </h2>
        {body && (
          <p
            style={{
              margin: 0,
              fontSize: '15px',
              lineHeight: 1.5,
              color: 'var(--c--theme--colors--greyscale-700, #444)',
            }}
          >
            {body}
          </p>
        )}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={styles.ooEditorContainer}
    >
      {/* OnlyOffice replaces this div with its own iframe[name="frameEditor"] */}
      <div id="oo-editor-placeholder" />
      {/* Loading overlay */}
      {state !== 'ready' && state !== 'oo-crashed' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '16px',
            background: 'white',
            zIndex: 10,
          }}
        >
          <Loader />
          <span style={{ color: 'var(--c--theme--colors--greyscale-600, #666)' }}>
            {state === 'decrypting' &&
              t('explorer.encrypted.decrypting', 'Decrypting...')}
            {state === 'converting' &&
              t('explorer.encrypted.converting', 'Preparing editor...')}
            {state === 'syncing-history' &&
              t(
                'explorer.encrypted.syncing_history',
                'Syncing collaborative state...',
              )}
            {state === 'stale-resyncing' &&
              t(
                'explorer.encrypted.stale_resyncing',
                'Reconnecting after long disconnect — refetching document...',
              )}
            {(state === 'loading' || state === 'mounting') &&
              t('explorer.encrypted.loading_editor', 'Loading editor...')}
          </span>
        </div>
      )}
      {/* OO crash recovery overlay */}
      {state === 'oo-crashed' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '16px',
            padding: '24px',
            textAlign: 'center',
            background: 'white',
            zIndex: 20,
          }}
        >
          <span
            className="material-icons"
            style={{
              fontSize: '48px',
              color: 'var(--c--theme--colors--danger-600, #c00)',
            }}
          >
            sync_problem
          </span>
          <h2 style={{ margin: 0, fontSize: '18px' }}>
            {t(
              'explorer.encrypted.oo_crashed_title',
              'Synchronization error',
            )}
          </h2>
          <p
            style={{
              margin: 0,
              maxWidth: '520px',
              color: 'var(--c--theme--colors--greyscale-700, #444)',
              lineHeight: 1.5,
            }}
          >
            {t(
              'explorer.encrypted.oo_crashed_body',
              'An error occurred while synchronizing with other peers. ' +
                'Because the document is end-to-end encrypted, we cannot ' +
                'always reconcile changes perfectly. Please reload the ' +
                'editor to fetch the latest saved state.',
            )}
          </p>
          <button
            type="button"
            onClick={requestRecoveryReload}
            disabled={recoveryWaiting}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 20px',
              fontSize: '14px',
              fontWeight: 600,
              color: 'white',
              background: recoveryWaiting
                ? 'var(--c--theme--colors--greyscale-500, #888)'
                : 'var(--c--theme--colors--primary-600, #0366d6)',
              border: 'none',
              borderRadius: '4px',
              cursor: recoveryWaiting ? 'wait' : 'pointer',
            }}
          >
            {recoveryWaiting && (
              <span
                aria-hidden
                style={{
                  display: 'inline-block',
                  width: '14px',
                  height: '14px',
                  border: '2px solid rgba(255,255,255,0.45)',
                  borderTopColor: 'white',
                  borderRadius: '50%',
                  animation: 'oo-crashed-spin 0.8s linear infinite',
                }}
              />
            )}
            {recoveryWaiting
              ? t(
                  'explorer.encrypted.oo_crashed_waiting',
                  'Waiting for peers to save…',
                )
              : t('explorer.encrypted.oo_crashed_reload', 'Reload editor')}
          </button>
          <style>
            {'@keyframes oo-crashed-spin { to { transform: rotate(360deg); } }'}
          </style>
        </div>
      )}
      {/* Connection status — only show when there's a problem */}
      {relayFailed && (
        <div
          style={{
            position: 'absolute',
            bottom: 8,
            left: 8,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            background: 'var(--c--theme--colors--danger-100, #fde8e8)',
            color: 'var(--c--theme--colors--danger-600, #c00)',
            zIndex: 10,
            pointerEvents: 'none',
          }}
        >
          <span className="material-icons" style={{ fontSize: '14px' }}>
            cloud_off
          </span>
          {t('explorer.encrypted.relay_failed', 'Collaboration unavailable')}
        </div>
      )}
    </div>
  );
};
