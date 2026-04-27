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
import { extractMedia } from './odtBundle';
import { EXTENSION_TO_X2T_TYPE } from './types';
import { getEffectiveMimetype } from '@/features/explorer/utils/mimeTypes';
import { KeyMismatchPanel } from '@/features/encryption/KeyMismatchPanel';
import {
  consumePeerLocksShownToEditor,
  createMockServerCallbacks,
  resetPeerLocksShownToEditor,
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
import { resetPatchIndex, observeIncomingSaveChanges } from './changesPipeline';
import { EncryptedRelay } from './encryptedRelay';
import { WordLockArbitrator } from './wordLockArbitrator';
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
import { downloadDecryptedFile } from '@/features/items/hooks/useDecryptedContent';
import { ModalRecursiveRemoveEncryption } from '@/features/encryption/ModalRecursiveRemoveEncryption';
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
  injectCSS?: (css: string) => void;
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
  /**
   * Another peer crashed and its reload is about to trigger a room-wide
   * realignment (see `pendingRecoveryReinitRef`): we've observed the
   * `peer:needs-save` and we're waiting for the matching `save:committed`
   * so we can reinit from the same S3 bytes. Overlay shown during this
   * window so the user doesn't type edits that would be discarded by
   * the imminent reinit.
   */
  | 'peer-resyncing'
  | 'oo-crashed';

// Only these OO message types are allowed in from peers. Anything else (rpc,
// executeCommand, documentOpen, pluginEvent, forceSave, …) would be a way for
// a malicious peer to reach internal OO surfaces that aren't meant to be
// peer-driven, so the bridge drops them.
/**
 * Rough chain size threshold after which the leader broadcasts a
 * checkpoint reload. Measured as the length of the JSON-serialized
 * chain (saveChanges messages accumulated locally). A new joiner
 * needs to replay this entire chain on top of baseBin, so keeping it
 * small protects join latency. When crossed, leader snapshots OO via
 * `asc_nativeGetFile()` and ships the result as the new baseBin to
 * everyone; each peer then destroys + recreates its OO iframe from
 * that bin and resets its local chain to empty.
 *
 * Tuned conservative: 50 MB in JSON chars is hundreds of minutes of
 * active editing on a normal doc. In practice checkpoints fire
 * rarely and the "flash" is only visible under heavy sustained use.
 */
const CHECKPOINT_CHAIN_SIZE_BYTES = 50 * 1024 * 1024;

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
  if (
    !msg ||
    typeof msg.type !== 'string' ||
    !INBOUND_ALLOWLIST.has(msg.type)
  ) {
    console.warn(
      '[OOEditor] dropping inbound message with disallowed type:',
      msg?.type
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
  const [showRemoveEncryption, setShowRemoveEncryption] = useState(false);
  const [downloading, setDownloading] = useState(false);
  // Save-error banner state. The OO editor keeps running in both
  // cases — this only controls a banner overlay on top of it:
  //  - `fatal`: x2t refused the document (e.g. OLE-embedded xlsx in
  //    an odp slide). User must roll back or remove the offending
  //    content; retrying won't help.
  //  - `transient`: network / vault / extract hiccup. Clears on the
  //    next successful save; exposes a "Retry now" button.
  const [saveError, setSaveError] = useState<{
    kind: 'fatal' | 'transient';
    detail: string;
  } | null>(null);
  const [saveRetrying, setSaveRetrying] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [relayFailed, setRelayFailed] = useState(false);
  /**
   * Bumped when the relay tells us our history cursor is stale (close
   * code 4001). Each bump re-runs the init effect, which refetches the
   * S3 snapshot and builds a fresh editor. The old editor + relay are
   * torn down in the cleanup branch of the previous run.
   */
  const [reinitKey, setReinitKey] = useState(0);
  /**
   * User-driven escape hatch out of the `PEER_STATE_UNAVAILABLE`
   * error overlay: when set, init forces view mode and skips the
   * relay entirely (no peer:join, no state-request, no saveChanges).
   * The user gets a pure local read-only view of the S3 snapshot —
   * safe even when another peer is editing because we emit nothing.
   * Cleared on a manual reload (the user decided to retry the live
   * session). Bumping `reinitKey` when this flips re-runs init.
   */
  const [viewOnlyOverride, setViewOnlyOverride] = useState(false);
  /**
   * True while a "flush before close" save is in flight. When set, the
   * editor renders a full-screen overlay with a loader so the user
   * sees that we're persisting their work before the document closes.
   * Triggered by the close-button save guard (see useEffect below).
   */
  const [flushingOnClose, setFlushingOnClose] = useState(false);
  const editorRef = useRef<OOEditorInstance | null>(null);
  const relayRef = useRef<EncryptedRelay | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptLoadedRef = useRef(false);
  // Connected peers with edit capability (not including self). Keyed
  // by userId, value is the earliest `joinedAt` we've seen for that
  // user — so leader election can tiebreak across multiple same-user
  // tabs by comparing (userId, joinedAt) lexicographically.
  const editorPeersRef = useRef<Map<string, number>>(new Map());
  // Peers that have broadcast `peer:crashed` — they're still connected
  // (so they can observe `save:committed` and reload) but must be
  // excluded from leader election: a crashed editor can't run
  // `forceSave`. Cleared when the peer disconnects or we rejoin.
  const crashedPeersRef = useRef<Set<string>>(new Set());
  /**
   * Set true when a `peer:needs-save` arrives from a peer recovering
   * from a crash. The next `save:committed` broadcast we observe is
   * then the save that the crashed peer asked for, and we must reinit
   * ourselves from the fresh S3 bytes to keep our OO load-phase IDs
   * aligned with the recovering peer's fresh load. Without this
   * realignment, saveChanges we broadcast after the peer's reload
   * reference internal ids they no longer recognise (and vice-versa)
   * — the OT engine then silently drops those patches or crashes.
   *
   * Cleared after triggering reinit, or by a timeout if the save
   * never lands (leader dead, network wedged, etc).
   */
  const pendingRecoveryReinitRef = useRef(false);
  const pendingRecoveryReinitTimerRef = useRef<ReturnType<
    typeof setTimeout
  > | null>(null);
  /**
   * Peer state transfer (CryptPad-style). We keep the .bin OO loaded
   * from AND every saveChanges frame observed since that load, all
   * locally in memory. This is what we ship to a late joiner so they
   * rebuild OO with identical internal object ids — loading the
   * baseBin gives them our load-phase counter state, and replaying
   * the chain adds the edit-phase objects via `CChangesTableIdAdd`
   * (which carries each new object's id on the wire; OO's
   * `Read_FromBinary2` overwrites the locally-generated id with it).
   *
   * `baseBinRef` — the native-bin string we initialised OO with, or
   *   the new bin emitted by the last checkpoint. Frozen until the
   *   next checkpoint.
   * `chainRef` — ordered saveChanges messages, outgoing and incoming
   *   alike, since the current `baseBinRef` was adopted.
   * `peerStateDumpRef` — if a peer sends us state BEFORE our cold-
   *   start path finishes x2t conversion, we stash it here and the
   *   cold-start path picks it up instead of using its x2t output.
   */
  const baseBinRef = useRef<string | null>(null);
  const chainRef = useRef<Array<Record<string, unknown>>>([]);
  type PeerStateDump = {
    baseBin: string;
    chain: Array<Record<string, unknown>>;
  };
  const peerStateDumpRef = useRef<PeerStateDump | null>(null);
  /**
   * Resolver for the "bin decision" promise. Four possible outcomes:
   *   - `'peer'` — we received a live state-response (peer dump in
   *     `peerStateDumpRef`); init swaps the editor's source bin and
   *     replays the chain.
   *   - `'cold'` — `room:state` confirmed we're alone, or the last
   *     other editor left while we were waiting; init boots from our
   *     x2t-converted bin.
   *   - `'no-response'` — peers were present at `room:state`, we
   *     broadcast `peer:state-request`, and 15s elapsed without an
   *     `oo:state-response`. Booting from x2t here would corrupt the
   *     session: the active editor has live edit-phase ids and we'd
   *     start with mismatched cold-start ids, so every subsequent
   *     saveChanges would drift the document. Init bails to the error
   *     overlay instead, telling the user a peer is unresponsive.
   *   - `'no-relay'` — the WebSocket relay failed to connect, or
   *     `EncryptedRelay` construction threw (vault keys, etc). We
   *     have no way to know whether other peers are editing right
   *     now, so opening editable would risk corruption — same hard
   *     bail as `'no-response'` with a dedicated message.
   *
   * Init awaits this before creating OO, so the editor only boots
   * when we know which bytes to feed it.
   */
  const binDecisionResolveRef = useRef<
    ((r: 'peer' | 'cold' | 'no-response' | 'no-relay') => void) | null
  >(null);
  /**
   * True while we're expecting a peer state dump (we've broadcast a
   * `peer:state-request` and haven't received a response yet).
   * Cleared when the response arrives, or by a fallback timeout so we
   * don't hang forever if nobody replies (e.g. existing peers can't
   * edit, or all are read-only). The fallback after timeout is the
   * normal cold-start (our x2t-converted bin).
   */
  const awaitingPeerStateRef = useRef(false);
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
        '[OOEditor] entering crash state — outbound traffic silenced, relay closed'
      );
    }
    outgoingSilencedRef.current = true;
    // Broadcast `peer:crashed` so surviving peers drop us from their
    // leader election — a crashed editor can't run `forceSave`, so if
    // we happened to be the lexicographic leader the room would have
    // nobody to handle a `peer:needs-save`. We stay connected on
    // purpose: the websocket must remain open so we can observe the
    // subsequent `save:committed` broadcast and resolve the recovery
    // wait (spinner on the Reload button).
    try {
      relayRef.current?.sendCrashed();
    } catch (e) {
      console.warn('[OOEditor] sendCrashed failed', e);
    }
    // Note: we do NOT fire `peer:needs-save` here. The user may never
    // click Reload (e.g. closes the tab instead), and a crash storm
    // would otherwise spam the leader with forceSave requests. The
    // save is requested only on explicit Reload click, with the
    // wait-for-save:committed spinner.
    setState('oo-crashed');
  }, []);

  /**
   * Crash-recovery reload: before bumping `reinitKey` (which re-runs
   * the init effect and refetches the S3 snapshot), ask the room's
   * save-leader to persist immediately. Then wait for the
   * `save:committed` broadcast to arrive before bumping — that's the
   * signal the S3 object now reflects the latest live state. A hard
   * timeout falls through to a reinit against the older snapshot if
   * no one saves in time.
   *
   * While the wait is in progress the button shows a loader and is
   * disabled so the user can't double-click.
   */
  // Hard ceiling on the recovery wait — if no `save:committed` shows
  // up within this window (leader gone, network wedged), fall through
  // to a reinit against the older snapshot. `sendNeedsSave` was
  // already fired at crash time, so by the time the user clicks this
  // the save is often already done.
  const RECOVERY_SAVE_WAIT_MS = 10000;
  const [recoveryWaiting, setRecoveryWaiting] = useState(false);
  /** Fired by onRemoteSaveCommitted the moment a fresh save lands. */
  const recoveryResolveRef = useRef<(() => void) | null>(null);

  const requestRecoveryReload = useCallback(() => {
    if (recoveryWaiting) return;
    setRecoveryWaiting(true);

    // If no other non-crashed editor is in the room, nobody will
    // respond to `peer:needs-save` — skip the wait and reinit
    // immediately against the current S3 snapshot. The crashed user is
    // still connected to the relay (WebSocket stays open so it can
    // observe `save:committed`), so the room is not empty per se, but
    // there's no surviving editor that could ship us live state.
    const myId = user?.sub;
    const hasOtherSaver = [...editorPeersRef.current.keys()].some(
      id => id !== myId && !crashedPeersRef.current.has(id)
    );

    if (!hasOtherSaver) {
      setRecoveryWaiting(false);
      setState('stale-resyncing');
      setReinitKey(k => k + 1);
      return;
    }

    // Ask any surviving peer for live state. The leader on the receive
    // side will answer with their baseBin + chain; on arrival we tear
    // down and rebuild against it. If nobody answers in
    // `RECOVERY_SAVE_WAIT_MS`, the timer below falls through to a
    // plain S3 reinit.
    try {
      relayRef.current?.sendStateRequest();
    } catch (e) {
      console.warn('[OOEditor] sendStateRequest from reload failed', e);
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
    recoveryResolveRef.current = finish;
    setTimeout(finish, RECOVERY_SAVE_WAIT_MS);
  }, [recoveryWaiting, user?.sub]);

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
    []
  );

  /**
   * Dump the first few top-level content blocks (paragraphs / tables)
   * with their OO-internal `Id` and a short text preview. Used to
   * verify across peers / across reload whether the `.drive/editor.bin`
   * sidecar actually preserves internal object ids. Same visible text
   * with same `Id` across runs → ids preserved (sidecar works). Same
   * text with different `Id` → native-bin round-trip renumbers and
   * this approach is broken at the root.
   *
   * Exposed on `window.__driveLogIds()` for ad-hoc invocation from
   * devtools — useful to re-check the state after any edit.
   */
  const logParagraphIds = useCallback((label: string) => {
    try {
      const ooIframe = document.querySelector(
        'iframe[name="frameEditor"]',
      ) as HTMLIFrameElement | null;
      const innerWindow = ooIframe?.contentWindow as any;
      const innerEditor = innerWindow?.editor || innerWindow?.editorCell;
      // OO exposes a few aliases; walk them defensively.
      const logicDoc =
        innerEditor?.WordControl?.m_oLogicDocument ??
        innerEditor?.wb?.oApi?.WordControl?.m_oLogicDocument ??
        innerEditor?.getLogicDocument?.();
      const content: unknown = logicDoc?.Content;
      if (!Array.isArray(content)) {
        console.log(
          `[id-diag ${label}] document not accessible yet (content missing)`,
        );
        return;
      }
      const preview = content.slice(0, 5).map((el: any, i: number) => {
        let text = '';
        try {
          if (typeof el.GetText === 'function') {
            text = String(el.GetText()).slice(0, 60);
          } else if (typeof el.Get_Text === 'function') {
            text = String(el.Get_Text()).slice(0, 60);
          }
        } catch {
          /* ignore */
        }
        return {
          idx: i,
          Id: el?.Id,
          cls: el?.constructor?.name,
          text,
        };
      });
      console.log(
        `[id-diag ${label}] total=${content.length} first5:`,
        preview,
      );
    } catch (e) {
      console.warn('[id-diag] failed', e);
    }
  }, []);

  // Expose the diagnostic globally so it can be triggered from devtools
  // at any moment — "type on one side, call `__driveLogIds()` on both"
  // is a quick way to eyeball whether the IDs referenced in the live
  // saveChanges resolve on both peers.
  if (typeof window !== 'undefined') {
    (window as any).__driveLogIds = (label?: string) =>
      logParagraphIds(label ?? 'manual');
  }

  /**
   * Called once OO reports documentContentReady. Waits the pre-delay
   * then flushes the FIFO buffer in arrival order.
   */
  const releaseReplayAfterPreDelay = useCallback(() => {
    console.log(
      `[replay] scheduling release after ${DRAIN_PRE_DELAY_MS} ms pre-delay ` +
        `(buffered=${replayBufferRef.current.length})`
    );
    setTimeout(() => {
      console.log(
        '[replay] pre-delay elapsed — flushing',
        replayBufferRef.current.length,
        'buffered events in arrival order'
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
      // Only now flip to 'ready' — the loading overlay has been
      // covering the editor while the replay queue was being fed to
      // OO, so users don't see chain entries appearing in realtime.
      // `onDocumentReady` fires earlier (when OO's base document is
      // loaded) and we used to setState there, which exposed the
      // mid-replay flickering. Moving the transition here means the
      // user sees a clean final doc as soon as the overlay clears.
      setState(current =>
        current === 'ready' || current === 'oo-crashed'
          ? current
          : 'ready',
      );
    }, DRAIN_PRE_DELAY_MS);
  }, []);
  // `viewOnlyOverride` flips us to local read-only without changing
  // the underlying ability — same code path as a true reader, so the
  // mode prop, relay gating and leader-election all become no-ops
  // automatically.
  const canEdit =
    !!item.abilities?.partial_update && !viewOnlyOverride;

  // For encrypted items the server stores `application/octet-stream` (it
  // can't sniff ciphertext). `getEffectiveMimetype` falls back to the
  // filename extension so the MIME_TO_* lookups below don't all miss and
  // mislabel an .odp/.ods as .docx — x2t would then refuse the ZIP with
  // "content corresponds to presentations, but inconsistent extension".
  const mime = getEffectiveMimetype(item) || '';
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
   * Put the OO editor into document-model-level read-only ("restricted")
   * mode when the user can't edit. OnlyOffice exposes
   * `asc_setRestriction(true)` on its editor controller, which gates
   * LOCAL inputs at the model layer without touching the co-edit patch
   * pipeline — inbound OT ops continue to stream in and render live,
   * but the user's own keystrokes / clicks / menu actions no longer
   * mutate the document.
   *
   * Reached via `window.frames[0].editor` for word / slide, or
   * `.editorCell` for spreadsheet (xlsx/ods), matching the split OO's
   * sdk-all does internally.
   *
   * Must be called after `onDocumentReady` — the editor controller
   * isn't attached to the iframe window before that.
   */
  /**
   * CSS patches that apply to EVERY user regardless of edit rights.
   *
   * The in-browser x2t WASM we bundle can't produce certain targets
   * that the stock OnlyOffice "Download As" picker still advertises:
   *   - `epub`, `fb2`, `rtf` — the WASM build lacks those writers
   *     (`_ZN9CEpubFileC1Ev` etc. are missing, aborts the conversion).
   *   - `jpg`, `png` — docs/sheets/slides → single image isn't a flow
   *     x2t supports; it falls through to a `zip` target that also
   *     fails step 2 of the two-step fallback.
   * Hiding the tiles is better UX than letting a user click one and
   * get an opaque "conversion failed" error. The selector targets the
   * `format-ext` attribute OO itself sets on each format-item.
   */
  const applyGlobalBundleWorkarounds = useCallback(() => {
    if (!editorRef.current?.injectCSS) return;
    // Which "Download as" targets the bundled x2t WASM fails on
    // varies by docType. What matters:
    //   - epub/fb2/rtf: writers live in docbuilder (V8 + builder
    //     scripts), not in the pure-C++ x2t core; only the document
    //     editor's picker even offers them, so listing them for
    //     word-type only is harmless and precise.
    //   - jpg/png from DOCUMENT: doc → image isn't a real x2t flow;
    //     falls through to `zip` step 2 which errors out.
    //     jpg/png from PRESENTATION: reuses the same per-slide
    //     raster pipeline that powers thumbnails — compiled in, works.
    //     jpg/png from SPREADSHEET: untested here; hidden to be safe
    //     until proven otherwise.
    // Each tile renders the extension as a class on its SVG icon div
    // (`.svg-format-<ext>`). The `format="<n>"` attribute on the
    // button is a numeric type code that doesn't identify the ext
    // textually, so we key off the SVG class.
    let unsupported: string[];
    if (docType === 'word') {
      unsupported = ['epub', 'fb2', 'rtf', 'jpg', 'png'];
    } else if (docType === 'slide') {
      // Slides handle jpg/png via the thumbnail renderer
      unsupported = [];
    } else if (docType === 'cell') {
      // xlsb is the "Excel Binary Workbook" format — the bundled x2t
      // WASM doesn't include the writer
      unsupported = ['xlsb'];
    } else {
      unsupported = [];
    }
    const hideRule = unsupported
      .map(
        ext =>
          `.format-item:has(.svg-format-${ext}) { display: none !important; }`
      )
      .join('\n');
    try {
      editorRef.current.injectCSS(hideRule);
    } catch (err) {
      console.warn('[OOEditor] injectCSS for unsupported formats failed', err);
    }
  }, [docType]);

  const applyReadOnlyRestriction = useCallback(() => {
    if (canEdit) return;

    const ooIframe = document.querySelector(
      'iframe[name="frameEditor"]'
    ) as HTMLIFrameElement | null;
    const innerWindow = ooIframe?.contentWindow as
      | {
          editor?: { asc_setRestriction?: (v: boolean) => void };
          editorCell?: { asc_setRestriction?: (v: boolean) => void };
        }
      | undefined;
    if (!innerWindow) return;

    const ooEditor =
      docType === 'cell' ? innerWindow.editorCell : innerWindow.editor;
    if (ooEditor && typeof ooEditor.asc_setRestriction === 'function') {
      try {
        ooEditor.asc_setRestriction(true);
      } catch (err) {
        console.warn('[OOEditor] asc_setRestriction(true) failed', err);
      }
    }

    // Reader-specific UI patches injected into the OO iframe:
    //  - Hide the ribbon. `permissions.*` doesn't collapse it on
    //    sdk-all v9 — tabs stay rendered, just with buttons disabled —
    //    so we hide `#toolbar` explicitly.
    //  - Hide the chat compose area (`#chat-options` wraps both the
    //    textarea and the Send button). The chat panel's message log
    //    above stays visible and scrollable — readers still see every
    //    message editors post live. They just don't have an input to
    //    mash, which is cleaner than greying one out.
    //  - Relay-side: outbound chat frames from non-canEdit sockets
    //    are already dropped as binary, so this is pure UX polish on
    //    top of existing server-side enforcement.
    // The window-resize dispatch that follows is what prevents the
    // freed bands from leaving empty rectangles — OO re-lays out on
    // the event and reclaims the space.
    if (editorRef.current?.injectCSS) {
      try {
        editorRef.current.injectCSS(
          [
            '#toolbar { display: none !important; }',
            '#chat-options { display: none !important; }',
          ].join('\n')
        );
      } catch (err) {
        console.warn('[OOEditor] injectCSS failed', err);
      }
    }
    // Dispatch on both windows: the outer one (our app) and the OO
    // iframe's contentWindow. OO's internal layout listener lives in
    // the iframe; the outer trigger is cheap insurance for
    // nested-frame variants where the listener attaches higher up.
    try {
      window.dispatchEvent(new Event('resize'));
      const iframeWin = (
        document.querySelector(
          'iframe[name="frameEditor"]'
        ) as HTMLIFrameElement | null
      )?.contentWindow;
      iframeWin?.dispatchEvent(new Event('resize'));
    } catch {
      /* non-fatal */
    }
  }, [canEdit, docType]);

  /**
   * Upload encrypted content to S3.
   */
  const uploadEncrypted = useCallback(
    async (
      content: ArrayBuffer,
      _format: string,
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
      // Auto-save path: re-encrypt with the file's existing K_file. In the
      // hierarchical case, entry + chain resolves down to K_file; in the
      // flat case, entry itself is the K_file wrap.
      const { encryptedData } =
        encryptedKeyChain.length > 0
          ? await vaultClient.encryptWithKey(
              content,
              entryKeyBytes.buffer.slice(0),
              encryptedKeyChain.map(k => k.slice(0))
            )
          : await vaultClient.encryptWithKey(
              content,
              entryKeyBytes.buffer.slice(0)
            );

      // Get a presigned S3 upload URL for the existing file key.
      // S3 versioning keeps previous versions — no new filename needed.
      const urlResponse = await fetchAPI(
        `items/${item.id}/encryption-upload-url/`,
        {
          method: 'POST',
          body: JSON.stringify({}),
          headers: { 'Content-Type': 'application/json' },
        },
        { redirectOn40x: false }
      );
      const { upload_url: uploadUrl } = await urlResponse.json();

      // Upload encrypted content to S3 via presigned URL (XHR like regular Drive uploads)
      const encryptedBytes = new Uint8Array(encryptedData);
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', uploadUrl);
        xhr.setRequestHeader('X-amz-acl', 'private');
        xhr.setRequestHeader('Content-Type', 'application/octet-stream');
        xhr.addEventListener('error', () =>
          reject(new Error('S3 upload network error'))
        );
        xhr.addEventListener('abort', () =>
          reject(new Error('S3 upload aborted'))
        );
        xhr.addEventListener('readystatechange', () => {
          if (xhr.readyState === 4) {
            if (xhr.status === 200) {
              resolve();
            } else {
              reject(
                new Error(
                  `S3 upload failed: ${xhr.status} — ${xhr.responseText.slice(0, 200)}`
                )
              );
            }
          }
        });
        xhr.send(encryptedBytes);
      });

      // Signal peers that we've flushed a fresh rendered archive to S3
      // — they'll clear their local "unsaved" marker. S3 is for
      // cold-start recovery only; alignment between live peers is
      // handled peer-to-peer.
      relayRef.current?.sendSaveCommitted();
    },
    [item.id]
  );

  /**
   * Close-button save guard.
   *
   * The preview-modal close path runs synchronously: parent calls
   * `setPreviewItem(undefined)`, React unmounts OOEditor, the iframe
   * is removed before our cleanup runs — so any save attempt from
   * cleanup is too late (the iframe is already gone).
   *
   * Solution: register a window-level async guard that the parent
   * `await`s BEFORE unmounting. When triggered, we flip
   * `flushingOnClose` so an overlay covers the editor with a loader,
   * call `forceSave`, and return. The parent then unmounts.
   *
   * Tab close / refresh take a different path: `beforeunload` fires
   * the native browser confirm, and on "Stay" we still have the iframe
   * alive (handled by `handleVisibilityChange` and the auto-save tick).
   * We can't render an overlay during a real unload — the page is
   * already navigating — so the native confirm is the best we can do.
   */
  useEffect(() => {
    const guard = async (): Promise<void> => {
      if (!isSaveLeaderRef.current()) return;
      if (!hasUnsavedChanges()) return;
      // Iframe is still mounted at this point — the guard fires
      // BEFORE React tears down the subtree, so `forceSave` can read
      // the live document state.
      setFlushingOnClose(true);
      try {
        await forceSave();
      } catch (e) {
        console.error('[OOEditor] flush-on-close save failed', e);
      } finally {
        setFlushingOnClose(false);
      }
    };
    const w = window as unknown as {
      __driveOOEditorSaveGuard?: () => Promise<void>;
    };
    w.__driveOOEditorSaveGuard = guard;
    return () => {
      // Only clear if it's still ours — a remount may have already
      // overwritten the slot with a fresh instance's guard.
      if (w.__driveOOEditorSaveGuard === guard) {
        delete w.__driveOOEditorSaveGuard;
      }
    };
  }, []);

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
      // the editor.
      if (src && /\/sdkjs\/|sdk-all/.test(src)) return true;
      // Fallback: also match stacks whose message mentions sdkjs
      // symbols but whose `filename` was lost (cross-frame rethrow).
      return /sdk-all|\bAsc(?:Common|Format|Word)\b|CDocument\.|CCollaborative/.test(
        msg
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
          '[OOEditor] init() session reset — clearing refs, unsilencing outbound'
        );
        documentReadyRef.current = false;
        innerWindowRef.current = null;
        pendingRemoteChangesRef.current = [];
        replayBufferRef.current = [];
        replayPreDelayActiveRef.current = true;
        outgoingSilencedRef.current = false;
        crashedPeersRef.current.clear();
        recoveryResolveRef.current = null;
        // Reset peer-state transfer bookkeeping. Do NOT wipe
        // `peerStateDumpRef` here — when `onPeerStateResponse`
        // receives a dump mid-session it sets the ref AND bumps
        // `reinitKey` to trigger a fresh mount; wiping it here would
        // clobber that hand-off and the new mount would fall back to
        // cold-start (x2t) without ever consuming the live state.
        // The dump is consumed (and cleared) further down, in the
        // convert step.
        awaitingPeerStateRef.current = false;
        baseBinRef.current = null;
        chainRef.current = [];
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
        // S3 archive is the cold-start source — IDs are always
        // regenerated on load from the x2t-produced bin. The peer-
        // to-peer state-dump flow (in the relay callbacks) overrides
        // this with live state from an existing peer if one is
        // present, which preserves cross-peer id alignment.
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

        // Step 3: Convert the rendered .odt to OO's internal .bin via
        // x2t. We always run this so we have a fallback bin ready if
        // the room turns out to be empty (or peers don't respond in
        // time). When a peer DOES ship us live state via
        // `oo:state-response`, the block after the preload await
        // swaps the editor's source bin to the peer's baseBin and
        // replays their chain — the bin produced here is discarded.
        setState('converting');
        const converted = await convertToInternal(decryptedBuffer, filename);
        const bin: Uint8Array = converted.bin;
        let extractedImages: Array<{ name: string; data: Uint8Array }> =
          converted.images;
        if (cancelled) return;

        // Step 4: Create blob URL and load editor
        const blob = new Blob([bin], {
          type: 'application/octet-stream',
        });
        // `let` so we can swap in a peer-provided blob after the
        // bin-decision wait below.
        let blobUrl = URL.createObjectURL(blob);

        // Initialize participant tracking
        // Use user.sub (OIDC subject) — same ID the relay server uses
        const localUser = initLocalUser(
          user.sub!,
          user.full_name || user.email
        );
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
            // Always stay in 'edit' mode so the co-edit session machinery
            // remains wired — inbound OT patches only stream in when the
            // editor is part of a cooperating session. Switching to 'view'
            // gives OO's standalone viewer, which doesn't apply live
            // patches and breaks the "reader watches editor type" UX.
            //
            // What actually makes a reader read-only is the `permissions`
            // block below: OO applies inbound patches from the co-edit
            // channel regardless of those, but gates LOCAL input on them.
            // Combined with the collab relay dropping any binary frame
            // from a non-canEdit socket (relay.ts:269), readers are pure
            // observers while still seeing every keystroke live.
            mode: 'edit',
            user: {
              id: uniqueOOId,
              name: user.full_name || user.email,
            },
            lang: user.language || 'en',
            // Force Fast co-editing mode and prevent the user from
            // switching to Strict. Our whole relay pipeline assumes
            // per-keystroke OT patches via `Continue_FastCollaborativeEditing`.
            // Strict mode uses paragraph-level lock acquisition
            // (`getLock`/`unLockDocument`/`releaseLock`) arbitrated
            // by a real DocServer — shapes we can't reconstruct on
            // the receiving peer, which crashes OO with the same
            // `undefined.guid`/`undefined.type` family we've been
            // chasing. `change: false` hides the toggle in Advanced
            // Settings so a user can't flip it mid-session.
            coEditing: {
              mode: 'fast',
              change: false,
            },
            customization: {
              compactToolbar: false,
              // In production we hide OO's own Save button — saving
              // is entirely owned by our checkpointing layer, and
              // users shouldn't need a manual save at all. In dev we
              // expose it so Cmd+S works through OO's native route
              // (our `onForceSaveRequest` handler picks it up without
              // echoing any ack, so OO's crash-prone `_onForceSave`
              // response path is never hit).
              forcesave: process.env.NODE_ENV === 'development',
              // `autosave: true` is REQUIRED: OO's internal
              // `_autoSave` timer is what drives
              // `Continue_FastCollaborativeEditing`, i.e. the OT
              // flush that ships saveChanges to peers. Turning this
              // off silently breaks live collaboration — the editor
              // keeps typing locally but remote peers stop seeing
              // updates. Do not disable.
              autosave: true,
              macros: false,
              plugins: false,
              help: false,
              // NOTE: we intentionally do NOT set
              // `customization.spellcheck` here — that path is
              // deprecated in current OO (the sdk even emits a
              // "Obsolete" console warning) and, more importantly,
              // does not actually stop the SpellCheck worker from
              // starting. The worker is disabled at runtime via
              // `editor.asc_setSpellCheck(false)` right after the
              // editor is ready (see the `innerEditor` setup block
              // further down in this effect).
              // Hide OO's chat panel for read-only users so they don't
              // see a writable input that goes nowhere. Editors keep
              // it — chat messages ride the same relay channel as
              // other OO `message` payloads (see `sendMessage` in
              // encryptedRelay.ts), so they broadcast end-to-end
              // encrypted between editor peers.
              chat: true,
            } as any,
            // Single source of truth for permissions — there used to be
            // TWO `permissions` blocks on this object, the second one
            // silently overriding the first. For readers, everything
            // that could mutate the document (edit, comment, review,
            // forms, content controls, filters) is off; `copy: false`
            // additionally blocks selection-based exfiltration. None of
            // these gate INBOUND OT, so live patches still stream in.
            permissions: {
              edit: canEdit,
              comment: canEdit,
              review: canEdit,
              fillForms: canEdit,
              modifyContentControl: canEdit,
              modifyFilter: canEdit,
              copy: canEdit,
              chat: true,
              deleteCommentAuthorOnly: false,
              editCommentAuthorOnly: false,
              macros: 'none',
              protect: false,
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
                  'iframe[name="frameEditor"]'
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
                      const ext = (
                        img.name.split('.').pop() || 'png'
                      ).toLowerCase();
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
                            img.data.subarray(offset, offset + chunkSize)
                          )
                        );
                      }
                      const dataUrl = `data:${mime};base64,${btoa(binary)}`;
                      docUrls.addImageUrl(img.name, dataUrl);
                    } catch (e) {
                      console.warn(
                        '[OOEditor] failed to register image',
                        img.name,
                        e
                      );
                    }
                  }
                  console.log(
                    '[OOEditor] registered',
                    extractedImages.length,
                    'images in g_oDocumentUrls'
                  );
                }

                // Also register any media that arrived inline with the
                // history replay (images pasted by peers before we joined).
                // Without this, references in the replayed saveChanges
                // would 404 on the next image load cycle.
                if (docUrls) {
                  for (const [name, url] of Object.entries(
                    historyInitialMedia
                  )) {
                    try {
                      docUrls.addImageUrl(name, url);
                    } catch (e) {
                      console.warn(
                        '[OOEditor] failed to register history media',
                        name,
                        e
                      );
                    }
                  }
                }
              } catch (e) {
                console.warn('[OOEditor] image registration failed', e);
              }
            },
            onDocumentReady: () => {
              // State transition to 'ready' is deferred to the end
              // of `releaseReplayAfterPreDelay` — otherwise the user
              // would see the overlay lift while OO is still
              // streaming chain entries into the view, producing
              // visible mid-replay flickering. Only `documentReadyRef`
              // needs to flip here so code that gates on "OO model is
              // live" continues to work.
              documentReadyRef.current = true;
              // `permissions.edit: false` in the config doesn't actually
              // block raw keystrokes on sdk-all v9 — a reader could
              // focus the canvas and type. OO's own internal knob for
              // this is `asc_setRestriction(true)` on the editor
              // controller. It gates local inputs at the document-model
              // level while leaving the co-edit inbound-patch pipeline
              // fully active, so readers keep seeing every keystroke
              // stream in from editors.
              applyGlobalBundleWorkarounds();
              applyReadOnlyRestriction();
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
                // DIAGNOSTIC: log the first few paragraphs' internal ids
                // so we can verify across peers / across a reload whether
                // the `.drive/editor.bin` sidecar actually preserves them.
                // If paragraph with same visible text has same `Id` on
                // u1 and u2 → IDs are preserved and the sidecar is doing
                // its job. If different ids for same content → the
                // native-bin round-trip renumbers objects and our
                // approach needs rethinking.
                logParagraphIds('post-load');
              };
              try {
                const ooIframe = document.querySelector(
                  'iframe[name="frameEditor"]'
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
                  const orig =
                    innerEditor.onDocumentContentReady.bind(innerEditor);
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
                  'iframe[name="frameEditor"]'
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
                      const msg = String(evt.reason?.stack ?? evt.reason ?? '');
                      handleOOError({
                        filename: '',
                        message: msg,
                        error: evt.reason,
                      } as ErrorEvent);
                    },
                  );
                }

                // Neutralise the SpellCheck worker at construction
                // time. The deprecated `customization.spellcheck` is
                // ignored by current OO and the runtime toggle
                // `asc_setSpellCheck(false)` only skips consulting
                // the worker — it doesn't prevent the worker from
                // starting or from posting messages back through its
                // MessagePort. The worker occasionally posts a reply
                // that's missing the expected `SpellCheckResponse` /
                // `SuggestResponse` field, and `SpellCheck_CallBack`
                // then crashes reading `.SpellCheckResponse` on
                // `undefined`.
                //
                // We intercept `new Worker(...)` inside the iframe:
                // when the URL points at OO's spell check worker
                // (`spell.js` / `spell_ie.js`, see `worker_src` in
                // sdk-all-min), return a no-op stub that never fires
                // `oncommand`/`onmessage`. For any other Worker we
                // defer to the original constructor unchanged.
                //
                // Timing: this runs on the post-content-ready hook,
                // which is early enough for most flows — OO lazily
                // creates the SpellCheck worker on first need, not
                // at script-load time, so we're ahead of its
                // instantiation. If OO ever changes to eager
                // creation this would need to move earlier.
                try {
                  if (
                    innerWindow &&
                    !innerWindow.__driveSpellWorkerNeutralised
                  ) {
                    innerWindow.__driveSpellWorkerNeutralised = true;
                    const OrigWorker = innerWindow.Worker;
                    if (OrigWorker) {
                      const isSpellCheckUrl = (u: unknown) => {
                        const s = String(u);
                        return (
                          /\bspell(?:_ie)?\.js\b/.test(s) ||
                          /\/sdkjs\/.*spell/i.test(s)
                        );
                      };
                      innerWindow.Worker = function PatchedWorker(
                        this: unknown,
                        url: string | URL,
                        options?: WorkerOptions,
                      ) {
                        if (isSpellCheckUrl(url)) {
                          console.log(
                            '[OOEditor] spell-check worker neutralised:',
                            String(url),
                          );
                          const noop = () => undefined;
                          return {
                            postMessage: noop,
                            terminate: noop,
                            addEventListener: noop,
                            removeEventListener: noop,
                            dispatchEvent: () => false,
                            onmessage: null,
                            onerror: null,
                            onmessageerror: null,
                          } as unknown as Worker;
                        }
                        return new OrigWorker(url, options);
                      } as unknown as typeof Worker;
                      // Preserve prototype chain so `instanceof Worker`
                      // checks in OO internals don't flip.
                      innerWindow.Worker.prototype = OrigWorker.prototype;
                    }
                  }
                } catch (e) {
                  console.warn(
                    '[OOEditor] failed to neutralise spell-check worker',
                    e,
                  );
                }

                // Disable unsupported features in the encrypted editor.
                // Our client-side x2t WASM can't handle Charts or
                // SmartArt — these require the full Document Server
                // (which only the non-encrypted WOPI path uses).
                // Inserting one produces unrecoverable save failures.
                // We mimic OO's own disabled-button look
                // (dim + pointer-events:none) rather than hiding the
                // button, so users see it's intentionally off.
                if (!innerWindow.__driveUnsupportedDisabled) {
                  innerWindow.__driveUnsupportedDisabled = true;
                  const doc = innerWindow.document;

                  // Button IDs differ between editors:
                  //   presentation: slot-btn-insertchart, slot-btn-inssmartart
                  //   calc:         slot-btn-inschart,    slot-btn-inssmartart
                  //   writer:       slot-btn-inschart,    slot-btn-inssmartart
                  const unsupportedButtons = [
                    {
                      slotId: 'slot-btn-insertchart',
                      menuId: 'id-toolbar-menu-insertchart',
                      label: 'Charts',
                    },
                    {
                      slotId: 'slot-btn-inschart',
                      menuId: 'id-toolbar-menu-inschart',
                      label: 'Charts',
                    },
                    {
                      slotId: 'slot-btn-inssmartart',
                      menuId: 'id-toolbar-menu-inssmartart',
                      label: 'SmartArt',
                    },
                  ];

                  const applyToElement = (
                    slot: HTMLElement,
                    menuId: string,
                    label: string
                  ) => {
                    slot.style.setProperty('opacity', '0.4', 'important');
                    slot.style.setProperty(
                      'pointer-events',
                      'none',
                      'important'
                    );
                    slot.setAttribute(
                      'title',
                      `${label} is not available in encrypted documents`
                    );
                    const btn = slot.querySelector('button');
                    if (btn) {
                      btn.setAttribute('tabindex', '-1');
                      btn.setAttribute('aria-disabled', 'true');
                      (btn as HTMLElement).style.setProperty(
                        'cursor',
                        'default',
                        'important'
                      );
                    }
                    const menu = doc.getElementById(menuId);
                    if (menu) menu.innerHTML = '';
                  };

                  // Track which buttons we've already logged as
                  // disabled. The observer below fires on every DOM
                  // mutation inside the editor (very frequent during
                  // live editing), so without this guard we'd re-log
                  // "Charts button disabled (mutation)" dozens of
                  // times per second. The actual DOM work is cheap
                  // and idempotent so we still re-apply on each tick —
                  // only the log is gated.
                  const loggedDisabled = new Set<string>();
                  const tryApplyAll = (trigger: string) => {
                    for (const {
                      slotId,
                      menuId,
                      label,
                    } of unsupportedButtons) {
                      const slot = doc.getElementById(slotId);
                      if (slot) {
                        applyToElement(slot as HTMLElement, menuId, label);
                        if (!loggedDisabled.has(slotId)) {
                          loggedDisabled.add(slotId);
                          console.log(
                            `[OOEditor] ${label} button disabled (${trigger})`
                          );
                        }
                      }
                    }
                  };

                  // Immediate attempt for the case the Insert tab is
                  // already mounted (HMR, tab re-entry).
                  tryApplyAll('immediate');

                  // MutationObserver: catch the buttons the moment OO
                  // adds them to the DOM. We watch the entire body
                  // because the ribbon root isn't stable by id.
                  try {
                    const observer = new innerWindow.MutationObserver(() => {
                      tryApplyAll('mutation');
                    });
                    observer.observe(doc.body, {
                      childList: true,
                      subtree: true,
                    });
                    console.log(
                      '[OOEditor] unsupported-features MutationObserver installed'
                    );
                  } catch (e) {
                    console.warn(
                      '[OOEditor] unsupported-features observer failed',
                      e
                    );
                  }
                }

                // Pre-create OO's clipboard sanitization iframe with a
                // permissive sandbox. OO's CommonIframe_PasteStart sets
                // sandbox="allow-same-origin" (no allow-scripts), which
                // Chrome warns about and which breaks Cmd+V image paste.
                // By creating the element first under the same id, OO's
                // `if(!ifr)` check finds ours and skips its own creation.
                const cb = innerWindow?.AscCommon?.g_clipboardBase;
                if (
                  cb &&
                  !innerWindow.document.getElementById(cb.CommonIframeId)
                ) {
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
                    'allow-same-origin allow-scripts'
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
                if (
                  innerWindow?.AscCommon &&
                  !innerWindow.AscCommon.__driveImgUrlsPatched
                ) {
                  let imgCounter = 0;
                  innerWindow.AscCommon.sendImgUrls = function (
                    api: any,
                    images: any[],
                    callback: (
                      data: Array<{ url: string; path: string }>
                    ) => void
                  ) {
                    if (!api.isOpenedFrameEditor) {
                      api.sync_StartAction?.(
                        innerWindow.Asc?.c_oAscAsyncActionType
                          ?.BlockInteraction ?? 1,
                        innerWindow.Asc?.c_oAscAsyncAction?.LoadImage ?? 0
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
                      const ext = mimeMatch
                        ? mimeMatch[1].replace('+xml', '')
                        : 'png';
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
                        innerWindow.Asc?.c_oAscAsyncActionType
                          ?.BlockInteraction ?? 1,
                        innerWindow.Asc?.c_oAscAsyncAction?.LoadImage ?? 0
                      );
                    }
                    callback(out);
                  };
                  innerWindow.AscCommon.__driveImgUrlsPatched = true;
                }

                const innerEditor =
                  innerWindow?.editor || innerWindow?.editorCell;

                // Disable OnlyOffice's spell-check via the RUNTIME API,
                // not the deprecated `customization.spellcheck` config.
                // The OO sdk emits a deprecation log when the config
                // path is used and the engine itself ignores the value
                // — the SpellCheck worker still starts, still posts
                // back messages, and still crashes in
                // `SpellCheck_CallBack` when a response is malformed
                // (`Cannot read properties of undefined (reading
                // 'SpellCheckResponse')`). `asc_setSpellCheck(false)`
                // is the supported post-init toggle that actually
                // stops the worker from being consulted.
                try {
                  innerEditor?.asc_setSpellCheck?.(false);
                } catch (e) {
                  console.warn('[OOEditor] asc_setSpellCheck(false) failed', e);
                }

                // Force a unique-per-connection prefix for edit-phase
                // object ids. OO derives its `IdCounter` prefix from
                // `indexUser` in the participants list, which we set to
                // empty string so comment attribution stays consistent
                // with `config.user.id`. Consequence: edit-phase ids
                // end up as `_1`, `_2`, … with no user prefix — two
                // peers creating new paragraphs in parallel both
                // generate `_1`, collide, and the cross-broadcast
                // Apply_Data tries to insert an object whose id already
                // exists locally (silent drop at best, Apply_Data crash
                // at worst).
                //
                // Override by setting `m_sUserId` directly on the
                // singleton. We use `user.sub + '_' + relay.joinedAt`
                // so the suffix is unique not just per-user but per-
                // connection, in case the same Drive user opens the
                // doc in two tabs at once. Attribution (`idOriginal`
                // in participants, `user.id` in config) is untouched.
                try {
                  const suffix = `${user.sub ?? 'anon'}_${relayRef.current?.joinedAt ?? Date.now()}`;
                  const idCounter = innerWindow?.AscCommon?.g_oIdCounter;
                  if (idCounter?.Set_UserId) {
                    idCounter.Set_UserId(suffix);
                    console.log(
                      '[OOEditor] IdCounter prefix pinned to',
                      suffix,
                    );
                  }
                } catch (e) {
                  console.warn('[OOEditor] Set_UserId override failed', e);
                }


                // NOTE: apart from `asc_setSpellCheck` above we do not
                // monkey-patch sdkjs prototype methods. The known-
                // benign crashes surface via the window-level `error`
                // listener and trigger the recovery overlay; wrapping
                // individual prototypes proved fragile across OO
                // upgrades.

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
                      '_downloadAsUsingServer'
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
                      downloadType: unknown
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
        // Theme hooks: OO's ChangeTheme calls window.parent.APP.changeTheme
        // when the LOCAL user picks a slide theme. The patched SDK in this
        // bundle also calls APP.remoteTheme() when applying a remote peer's
        // theme change (cp_theme collaborative-change type). In both cases the
        // actual theme data already propagates through the normal OT
        // saveChanges pipeline (ChangeTheme creates a history point), so
        // these callbacks are purely notification hooks — no-ops are safe.
        (window as any).APP.changeTheme = (_indexTheme: number) => {
          /* no-op — theme change propagates via OT saveChanges */
        };
        (window as any).APP.remoteTheme = () => {
          /* no-op — remote theme applied by OO internally via ChangeTheme(id, null, true) */
        };
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
          files: FileList | File[]
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
                })
            )
          );
        };

        // Drag-and-drop / paste path.
        (window as any).APP.UploadImageFiles = (
          files: FileList | File[],
          _documentId: string,
          _documentUserId: string,
          _jwt: string,
          callback: (err: number | null, urls: string[]) => void
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
          callback: (result: unknown) => void
        ) => {
          (async () => {
            try {
              const ooIframe = document.querySelector(
                'iframe[name="frameEditor"]'
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
              const ext = (
                title.split('.').pop() || x2tExtension
              ).toLowerCase();
              const isPrint = ctx.downloadType === 'asc_onPrintUrl';

              let outBytes: Uint8Array<ArrayBuffer>;
              const mime = MIME_BY_EXT[ext] || 'application/octet-stream';

              if (ext === 'pdf') {
                const rawLayout = dataContainer?.data;
                if (!rawLayout) {
                  throw new Error(
                    'missing PDF layout bin (dataContainer.data)'
                  );
                }
                const layoutBuffer: ArrayBuffer =
                  rawLayout instanceof ArrayBuffer
                    ? rawLayout
                    : (rawLayout.buffer.slice(
                        rawLayout.byteOffset,
                        rawLayout.byteOffset + rawLayout.byteLength
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
                    Object.keys(urls)
                  );
                  // Also peek at OO's image cache — that's where inserted
                  // images actually live when they were passed as data URLs.
                  const imgCache =
                    innerWindow?.Asc?.editor?.ImageLoader?.map_image_index;
                  if (imgCache) {
                    console.log(
                      '[OOEditor] image cache keys:',
                      Object.keys(imgCache).map(k =>
                        k.length > 80 ? k.slice(0, 80) + '…' : k
                      )
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
                          e
                        );
                      }
                    })
                  );
                  console.log(
                    '[OOEditor] media files written to /working/media/:',
                    Array.from(media.keys())
                  );
                } catch (e) {
                  console.warn('[OOEditor] image gather failed', e);
                }
                console.log(
                  '[OOEditor] PDF layout (dataContainer.data) size:',
                  layoutBuffer.byteLength
                );
                outBytes = await convertFromInternalToPdf(
                  binBuffer,
                  layoutBuffer,
                  media
                );
              } else {
                const docType = EXTENSION_TO_X2T_TYPE[ext] || x2tType || 'doc';
                outBytes = await convertFromInternal(binBuffer, ext, docType);
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
          errorCb?: (err?: unknown) => void
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

        // Bin-decision promise: resolves as soon as `onRoomState`
        // reports we're alone in the room, or `onPeerStateResponse`
        // lands with live state from the leader, whichever comes
        // first. Falls through to 'cold' after 15s if neither —
        // generous enough to absorb slow leaders and big chains.
        // The `onPeerLeave` fast-path below resolves cold immediately
        // if the only other peer evicts during the wait, so this
        // timeout is really only the upper bound for unresponsive
        // real peers.
        //
        // Set up BEFORE `relay.connect()` so the callbacks wired in
        // the relay construction below can resolve it the instant
        // the first frames come in — even before the main flow has
        // reached the corresponding `await`.
        const BIN_DECISION_TIMEOUT_MS = 15_000;
        const binDecisionPromise = new Promise<
          'peer' | 'cold' | 'no-response' | 'no-relay'
        >(resolve => {
          const wrapped = (
            r: 'peer' | 'cold' | 'no-response' | 'no-relay',
          ) => {
            if (binDecisionResolveRef.current) {
              binDecisionResolveRef.current = null;
              resolve(r);
            }
          };
          binDecisionResolveRef.current = wrapped;
          // View-only override: we deliberately don't connect to the
          // relay, so no callback will ever resolve this promise.
          // Pre-resolve as `'cold'` so the convert step proceeds with
          // the x2t bin we already produced. We're emitting nothing,
          // so id alignment doesn't matter — the editor is purely
          // local.
          if (viewOnlyOverride) {
            wrapped('cold');
            return;
          }
          setTimeout(() => {
            if (!binDecisionResolveRef.current) return;
            // Final ghost-peer scrub before failing the user. The
            // `onRoomState` filter already excludes same-userId
            // peers and crashed peers, but in dev with React Strict
            // Mode (or HMR), a stale tab from a previous mount cycle
            // can still appear in `room:state` for a few hundred ms
            // before the server processes its close. If at the 15s
            // mark the live ref shows ZERO real other editors, the
            // initial "peers present" reading was a transient ghost
            // — fall back to `'cold'` instead of throwing the user
            // into the error overlay.
            const liveOthers = [...editorPeersRef.current.keys()].filter(
              id =>
                id !== user.sub && !crashedPeersRef.current.has(id),
            );
            console.warn(
              '[OOEditor] bin-decision timeout — peers snapshot:',
              {
                me: user.sub,
                peers: [...editorPeersRef.current.keys()],
                crashed: [...crashedPeersRef.current],
                liveOthers,
              },
            );
            if (liveOthers.length === 0) {
              console.warn(
                '[OOEditor] timeout but no real other editor remains — resolving cold (ghost peer evicted)',
              );
              binDecisionResolveRef.current('cold');
              return;
            }
            // Real other editor that just isn't responding. Don't
            // silently cold-start — that would race the live editor's
            // edit-phase ids and corrupt the document.
            binDecisionResolveRef.current('no-response');
          }, BIN_DECISION_TIMEOUT_MS);
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
            'media items'
          );
          resolveHistoryReady();
        };

        // Forward declaration so the relay callbacks can close over the
        // arbitrator, and so the mock server setup below can pass it in.
        // Populated once the relay is constructed (inside the try block).
        // Safe: the relay callbacks only fire on incoming network
        // messages, by which point the assignment below has happened.
        let wordLockArbitrator: WordLockArbitrator | null = null;

        // View-only override: bypass the relay entirely. No
        // peer:join, no state-request, no saveChanges — the user
        // wanted a safe local read-only view, so we don't even
        // announce our presence to the room. `endPreloadPhase()`
        // moves the state machine forward; `binDecisionPromise`
        // already resolved 'cold' synchronously above.
        if (viewOnlyOverride) {
          console.log(
            '[OOEditor] view-only override active — skipping relay setup',
          );
          endPreloadPhase();
        } else try {
          const relay = new EncryptedRelay({
            roomId: item.id,
            userId: user.sub!,
            userName: user.full_name || user.email,
            vaultClient,
            encryptedSymmetricKey: entryKeyBytes.buffer,
            encryptedKeyChain:
              encryptedKeyChain.length > 0 ? encryptedKeyChain : [],
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
                        e
                      );
                    }
                  }
                }

                // Preload and live phases now take the SAME path: queue
                // the change into pendingRemoteChangesRef if the editor
                // isn't ready yet, otherwise apply immediately. Every
                // inbound saveChanges flows through `sendMessageToOO`,
                // never through OO's `getInitialChanges` channel (which
                // silently drops replay bursts in our testing).
                if (!historyPhaseComplete) {
                  try {
                    const changes = (message as { changes?: unknown }).changes;
                    const n = Array.isArray(changes) ? changes.length : 0;
                    console.log(
                      `[HISTORY replay queued] changes=${n}`,
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
                    message as Record<string, unknown>
                  );
                  withIncomingOTGate(() => sendToEditorGuarded(message as any));
                };
                // Append to the local chain so we can replay it for
                // any future joiner asking us for state. Incoming
                // changes already carry sender ids baked in via
                // `CChangesTableIdAdd`, so a joiner applying the same
                // sequence on our baseBin ends up with identical
                // object ids.
                chainRef.current.push(
                  message as Record<string, unknown>,
                );
                // All saveChanges flow through the index-gated reorder
                // buffer. While the editor is still mounting / during
                // the post-ready pre-delay, the buffer holds events
                // until `releaseReplayAfterPreDelay` flushes them in
                // strict changesIndex order.
                handleIncomingSaveChanges(
                  message as Record<string, unknown>,
                  apply
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
                crashedPeersRef.current.delete(userId);
                // If we were waiting for this peer to ship us state
                // and they leave (e.g. the relay's ping/pong evicted
                // a ghost connection), don't keep spinning on the
                // 5s timeout — resolve cold now so the editor opens.
                const stillOtherEditors = [
                  ...editorPeersRef.current.keys(),
                ].filter(
                  id =>
                    id !== user.sub && !crashedPeersRef.current.has(id),
                );
                if (
                  stillOtherEditors.length === 0 &&
                  awaitingPeerStateRef.current
                ) {
                  console.log(
                    '[OOEditor] last other peer left while waiting — resolving cold',
                  );
                  awaitingPeerStateRef.current = false;
                  binDecisionResolveRef.current?.('cold');
                }
                // Capture the locks the peer held BEFORE `dropUser`
                // wipes them, then filter to the subset we actually
                // told OO about — pushing a `releaseLock` for a key
                // OO never heard of looks up an undefined paragraph
                // in the doc model and crashes (`Set_Type on undefined`).
                const leavingKeys = wordLockArbitrator
                  ? wordLockArbitrator
                      .snapshot()
                      .filter(e => e.userId === userId)
                      .map(e => e.key)
                  : [];
                const clearableKeys =
                  consumePeerLocksShownToEditor(leavingKeys);
                const leavingOOId =
                  getRemoteOOInternalId(userId) ?? userId;
                removeRemoteUser(userId);
                releaseAllUserLocks(userId);
                wordLockArbitrator?.dropUser(userId);
                if (
                  documentReadyRef.current &&
                  clearableKeys.length > 0
                ) {
                  sendToEditorGuarded({
                    type: 'releaseLock',
                    locks: clearableKeys.map(key => ({
                      block: key,
                      user: leavingOOId,
                      time: Date.now(),
                    })),
                  });
                }
                sendToEditor(buildConnectStateMessage() as any);
              },
              onRoomState: peers => {
                editorPeersRef.current.clear();
                crashedPeersRef.current.clear();
                for (const peer of peers) {
                  if (peer.userId) {
                    if (peer.canEdit) {
                      const existing = editorPeersRef.current.get(peer.userId);
                      if (existing === undefined || peer.joinedAt < existing) {
                        editorPeersRef.current.set(peer.userId, peer.joinedAt);
                      }
                    }
                    // Relay persisted the `peer:crashed` flag so a
                    // late joiner learns about it here rather than
                    // needing to witness the original broadcast.
                    if (peer.crashed) {
                      crashedPeersRef.current.add(peer.userId);
                    }
                    addRemoteUser(peer.userId, peer.userName, peer.userId);
                  }
                }
                sendToEditor(buildConnectStateMessage() as any);

                // If other editable peers are already in the room, ask
                // them to ship us their live state (baseBin + chain).
                // Only the leader on the receive side answers. Their
                // state-response lands in `peerStateDumpRef` and makes
                // the convert step skip its x2t output — OR, if OO
                // was already built, the response handler triggers a
                // reinit so we swap in the peer bin.
                const otherEditors = [...editorPeersRef.current.keys()].filter(
                  id =>
                    id !== user.sub && !crashedPeersRef.current.has(id),
                );
                if (
                  otherEditors.length > 0 &&
                  !outgoingSilencedRef.current &&
                  user.sub
                ) {
                  console.log(
                    '[OOEditor] joining with existing peers — requesting live state',
                    otherEditors,
                  );
                  awaitingPeerStateRef.current = true;
                  setState(current =>
                    current === 'ready' ? 'peer-resyncing' : current,
                  );
                  try {
                    relayRef.current?.sendStateRequest();
                  } catch (e) {
                    console.warn(
                      '[OOEditor] sendStateRequest on join failed',
                      e,
                    );
                  }
                } else {
                  // Alone in the room — init doesn't need to wait for
                  // a peer to ship us state. Unblock the bin-decision
                  // promise so the editor boots from the cold-start
                  // x2t bin immediately.
                  binDecisionResolveRef.current?.('cold');
                }
              },
              onLockUpdate: (type, userId, lockData) => {
                const lockId = JSON.stringify(lockData);
                if (type === 'acquire') {
                  acquireCellLock(lockId, userId, lockData);
                } else {
                  releaseCellLock(lockId, userId);
                }
                // _onGetLock iterates `locks` with `for (key in ...)` and
                // for cell/slide reads `lock.block.guid`. `lockData` is
                // the full `msg.block` array from the sender — iterate
                // each block element so the shape matches what OO expects.
                const remoteOOId = getRemoteOOInternalId(userId);
                const blockArray = Array.isArray(lockData)
                  ? lockData
                  : [lockData];
                const locks: Record<string, unknown> = {};
                for (const block of blockArray) {
                  const entry = {
                    block,
                    user: remoteOOId || userId,
                    time: Date.now(),
                  };
                  const guid = (block as any)?.guid;
                  const key =
                    guid ||
                    (typeof block === 'string' ? block : JSON.stringify(block));
                  locks[key] = entry;
                }
                const apply = () =>
                  sendToEditor({
                    type: 'getLock',
                    locks,
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
                // If init is still waiting on the bin-decision (the
                // ref is non-null until either a peer ships state, the
                // room is confirmed empty, or the 15s timeout fires),
                // reaching this callback means we never got a reliable
                // view of the room. Refuse to open editable — the
                // overlay's "Open in read-only" button is the safe
                // escape hatch.
                if (binDecisionResolveRef.current) {
                  binDecisionResolveRef.current('no-relay');
                }
                // Either way, unblock the preload await so the convert
                // step proceeds (it will throw for `'no-relay'`, or
                // continue normally if init already finished and this
                // is a mid-session reconnect failure — that case is
                // surfaced via the discreet `relayFailed` badge).
                endPreloadPhase();
              },
              onRemoteSaveCommitted: userId => {
                // A peer wrote a fresh rendered archive to S3. Just
                // clear our local "unsaved" marker so beforeunload
                // stops prompting; the live co-edit state stays on
                // the peer-to-peer channel.
                console.log('[OOEditor] remote save committed by', userId);
                markRemoteSaveCommitted();
                if (recoveryResolveRef.current) {
                  recoveryResolveRef.current();
                }
              },
              onPeerStateRequest: fromUserId => {
                // Someone joined and asked for live state. Only the
                // current leader answers, so we know no two peers
                // broadcast duplicate responses. The joiner will load
                // our baseBin + chain → end up with the exact same
                // internal object ids as us.
                if (!isSaveLeaderRef.current()) return;
                if (outgoingSilencedRef.current) return;
                const baseBin = baseBinRef.current;
                if (!baseBin) {
                  console.warn(
                    '[OOEditor] state request received but our baseBin is not ready yet',
                  );
                  return;
                }
                console.log(
                  '[OOEditor] answering state request from',
                  fromUserId,
                  'baseBin size:',
                  baseBin.length,
                  'chain size:',
                  chainRef.current.length,
                );
                void relayRef.current
                  ?.sendStateResponse(
                    fromUserId,
                    baseBin,
                    chainRef.current,
                  )
                  .catch(e => {
                    console.warn(
                      '[OOEditor] sendStateResponse failed',
                      e,
                    );
                  });
              },
              onPeerStateResponse: (fromUserId, baseBin, chain) => {
                console.log(
                  '[OOEditor] received state dump from',
                  fromUserId,
                  'baseBin size:',
                  baseBin.length,
                  'chain size:',
                  chain.length,
                );
                peerStateDumpRef.current = { baseBin, chain };
                awaitingPeerStateRef.current = false;
                // Resolve the init's bin-decision promise so the
                // waiting convert step can swap the editor's bin to
                // the peer dump before OO construction. If the
                // editor was ALREADY built (response arrived after
                // the 15s wait resolved 'cold'), trigger a reinit
                // to swap in the live state.
                if (binDecisionResolveRef.current) {
                  binDecisionResolveRef.current('peer');
                } else {
                  setState('peer-resyncing');
                  setReinitKey(k => k + 1);
                }
              },
              onCheckpointReload: (fromUserId, baseBin) => {
                // Leader-triggered full-room reload. Everyone stashes
                // the new baseBin as their dump and tears down OO —
                // we come back up with matching load-phase ids.
                console.log(
                  '[OOEditor] checkpoint reload from',
                  fromUserId,
                  'baseBin size:',
                  baseBin.length,
                );
                peerStateDumpRef.current = { baseBin, chain: [] };
                setState('peer-resyncing');
                setReinitKey(k => k + 1);
              },
              onPeerCrashed: peerUserId => {
                // A remote peer's editor entered the crash overlay.
                // Exclude it from our leader election so we don't
                // wait on a save that can never come. The peer will
                // reappear as a fresh connection (new joinedAt) if
                // it clicks Reload and reconnects.
                console.log(
                  '[OOEditor] peer',
                  peerUserId,
                  'crashed — excluding from leader election'
                );
                crashedPeersRef.current.add(peerUserId);
                // Also clear any paragraph locks the crashed peer was
                // holding so we don't keep denying askLock forever for
                // keys that will never be released — the peer is dead.
                if (wordLockArbitrator) {
                  const crashedKeys = wordLockArbitrator
                    .snapshot()
                    .filter(e => e.userId === peerUserId)
                    .map(e => e.key);
                  const clearableKeys =
                    consumePeerLocksShownToEditor(crashedKeys);
                  const crashedOOId =
                    getRemoteOOInternalId(peerUserId) ?? peerUserId;
                  wordLockArbitrator.dropUser(peerUserId);
                  if (
                    documentReadyRef.current &&
                    clearableKeys.length > 0
                  ) {
                    sendToEditorGuarded({
                      type: 'releaseLock',
                      locks: clearableKeys.map(key => ({
                        block: key,
                        user: crashedOOId,
                        time: Date.now(),
                      })),
                    });
                  }
                }
              },
              onWordLockRequest: (peerUserId, keys, timestampMs) => {
                if (!wordLockArbitrator) return;
                wordLockArbitrator.applyRemoteRequest(
                  { type: 'oo:lockRequest', userId: peerUserId, keys },
                  timestampMs,
                );
                // Deliberately NO push to local OO here. Before, we
                // echoed a full snapshot to mirror CryptPad, but that
                // referenced paragraphs OO didn't know about yet
                // (peer created + locked a new para before the
                // corresponding `saveChanges` applied) and crashed
                // OO in `_onGetLock` → `Set_UserId on undefined`.
                // Local OO only learns a key is peer-held when it
                // itself `askLock`s and we reply — at which point the
                // key is guaranteed to exist in the local doc model.
              },
              onWordLockRelease: (peerUserId, keys) => {
                if (!wordLockArbitrator) return;
                wordLockArbitrator.applyRemoteRelease({
                  type: 'oo:lockRelease',
                  userId: peerUserId,
                  keys,
                });
                // Only push `releaseLock` for keys we've previously
                // exposed to OO (via a `getLock` reply attributing
                // them to this peer). For any other key, OO doesn't
                // have a marker to clear, and referencing an unknown
                // paragraph by id crashes `_onReleaseLock` the same
                // way the `getLock` snapshot did.
                const clearableKeys = consumePeerLocksShownToEditor(keys);
                if (
                  documentReadyRef.current &&
                  clearableKeys.length > 0
                ) {
                  const peerOOId =
                    getRemoteOOInternalId(peerUserId) ?? peerUserId;
                  sendToEditorGuarded({
                    type: 'releaseLock',
                    locks: clearableKeys.map(key => ({
                      block: key,
                      user: peerOOId,
                      time: Date.now(),
                    })),
                  });
                }
              },
            },
          });
          relayRef.current = relay;

          // Now that the relay exists we can wire the arbitrator: its
          // transport is the relay's settlement-aware send helper. The
          // forward declaration at the top of this block is populated
          // here; the callbacks above see it through closure.
          wordLockArbitrator = new WordLockArbitrator({
            sendWithSettlement: msg => relay.sendEncryptedWithSettlement(msg),
          });
          // Fresh session → fresh tracking of which peer-owned locks
          // OO has been told about. Anything from a previous editor
          // lifecycle is irrelevant (and would point at a disposed
          // OO instance's paragraph ids).
          resetPeerLocksShownToEditor();

          // Install the leader-election implementation into the ref
          // BEFORE connecting the relay. Otherwise, incoming state-
          // requests from a peer that joins during our own init
          // window see the default `() => false` and we never
          // answer — u1 joins u2, sends state-request, u2's callback
          // thinks "I'm not leader", silently drops it, u1 falls
          // back to raw x2t. The closure captures `canEdit`/`user`
          // but reads the live peer map / relay joinedAt per call,
          // so it stays correct as peers join and leave.
          //
          // Election rule: EARLIEST `joinedAt` wins, with lex userId
          // as the tiebreak when two peers joined in the same ms. The
          // priority must be joinedAt first — if we ranked by lex
          // userId, a freshly-joined peer with a lex-smaller userId
          // would instantly steal the leader role from the existing
          // peer, who would then refuse to answer the joiner's own
          // `peer:state-request` (the joiner has no state to share).
          // Earliest-joinedAt also reflects "longest-lived peer is
          // most likely to have the freshest state", which matches
          // who should be checkpointing and saving.
          isSaveLeaderRef.current = () => {
            if (!canEdit) return false;
            // A crashed tab can't run `forceSave` — take ourselves
            // out of contention so the next candidate wins.
            if (outgoingSilencedRef.current) return false;
            const myId = user!.sub!;
            const myJoinedAt = relayRef.current?.joinedAt ?? 0;
            for (const [peerId, peerJoinedAt] of editorPeersRef.current) {
              // Peers whose editor crashed are still in the room
              // (they need to observe `save:committed`) but must not
              // be elected — skip them during the walk.
              if (crashedPeersRef.current.has(peerId)) continue;
              if (peerJoinedAt < myJoinedAt) return false;
              if (peerJoinedAt === myJoinedAt && peerId < myId)
                return false;
            }
            return true;
          };

          setState('syncing-history');
          relay.connect();
        } catch (relayErr) {
          console.warn('Relay setup failed:', relayErr);
          endPreloadPhase();
          // Same logic as `onReconnectFailed`: without a working
          // relay we can't tell whether other peers are editing, so
          // refuse to open editable. The user can pick "Open in
          // read-only" from the overlay if they just want to view
          // the document.
          binDecisionResolveRef.current?.('no-relay');
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
                console.warn('[OOEditor] preload outer timeout — proceeding');
                endPreloadPhase();
              }
              resolve();
            }, 120_000)
          ),
        ]);
        if (cancelled) return;

        // Wait for the bin-decision (the primed promise set up near
        // the top of init, resolved by relay callbacks above). Either:
        //   - `'peer'` — `onPeerStateResponse` landed, peerStateDumpRef
        //     is set with live state we should boot from
        //   - `'cold'` — `onRoomState` said we're alone (or the last
        //     other editor left while we were waiting); boot from the
        //     x2t bin we already prepared
        //   - `'no-response'` — peers were present but none answered
        //     within 15s; refuse to open the editor (cold-starting
        //     against a live session would corrupt ids).
        //   - `'no-relay'` — relay never connected; we can't see the
        //     room at all so we don't know if anyone is editing.
        //     Refuse to open editable for the same reason.
        const binDecision: 'peer' | 'cold' | 'no-response' | 'no-relay' =
          peerStateDumpRef.current ? 'peer' : await binDecisionPromise;
        if (cancelled) return;

        if (binDecision === 'no-response') {
          // Don't construct OO — we'd race the live editor with cold
          // x2t ids and silently corrupt the document. Surface a
          // dedicated error overlay so the user knows to retry.
          throw new Error(
            'PEER_STATE_UNAVAILABLE: another user is connected but did not respond with their live state.',
          );
        }
        if (binDecision === 'no-relay') {
          // Same risk as no-response: without a relay we can't tell
          // whether someone else is editing. The overlay reuses the
          // retry / read-only buttons.
          throw new Error(
            'RELAY_UNAVAILABLE: cannot reach the collaboration server.',
          );
        }

        // If a peer gave us live state, swap the editor's source bin
        // BEFORE construction so OO boots with their baseBin (and
        // thus their internal ids). Replay the chain through the
        // standard incoming-saveChanges pipeline; the pre-delay
        // buffer holds the apply functions until the editor fires
        // `onDocumentContentReady`, then flushes them in order.
        if (binDecision === 'peer' && peerStateDumpRef.current) {
          const peerDump = peerStateDumpRef.current;
          console.log(
            '[OOEditor] swapping editor bin to peer dump —',
            'baseBin size:',
            peerDump.baseBin.length,
            'chain size:',
            peerDump.chain.length,
          );
          // Release the old x2t blob URL so it can be GC'd.
          try {
            URL.revokeObjectURL(blobUrl);
          } catch {
            /* ignore */
          }
          const peerBinBytes = new TextEncoder().encode(peerDump.baseBin);
          const peerBlob = new Blob([peerBinBytes], {
            type: 'application/octet-stream',
          });
          blobUrl = URL.createObjectURL(peerBlob);
          config.document.url = blobUrl;
          baseBinRef.current = peerDump.baseBin;
          chainRef.current = [...peerDump.chain];
          for (const chainMsg of peerDump.chain) {
            const apply = () => {
              observeIncomingSaveChanges(
                chainMsg as Record<string, unknown>,
              );
              withIncomingOTGate(() =>
                sendToEditorGuarded(chainMsg as any),
              );
            };
            handleIncomingSaveChanges(
              chainMsg as Record<string, unknown>,
              apply,
            );
          }
          peerStateDumpRef.current = null;
        } else {
          // Cold start baseBin: decode the x2t output as the canonical
          // string form, so subsequent joiners we serve see the exact
          // bytes we loaded from.
          baseBinRef.current = new TextDecoder().decode(bin);
          chainRef.current = [];
        }

        // History replay is queued into `pendingRemoteChangesRef` above
        // and will be drained (paced) once OO fires `onDocumentContentReady`.
        // We do NOT use `setInitialChanges` / `getInitialChanges`: that
        // channel silently drops replay bursts in our testing. The
        // reliable path is `sendMessageToOO`.
        console.log(
          '[OOEditor:preload] ready to construct editor —',
          replayBufferRef.current.length,
          'saveChanges buffered,',
          pendingRemoteChangesRef.current.length,
          'ancillary events queued,',
          Object.keys(historyInitialMedia).length,
          'media items'
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
          // Word-only: hand the arbitrator to the mockServer so getLock
          // stops auto-granting and instead consults the replicated
          // lock table. `userId` lets the arbitrator attribute claims.
          // For cell/slide these stay undefined → mockServer falls back
          // to its existing optimistic path.
          wordLockArbitrator: wordLockArbitrator ?? undefined,
          userId: user.sub!,
          onSaveChangesBroadcast: message => {
            // A crashed editor must not leak its corrupt state to
            // peers — otherwise one broken tab takes down the whole
            // room when its autosave loop emits garbage that crashes
            // Apply_OtherChanges on every other client.
            if (outgoingSilencedRef.current) {
              console.warn(
                '[OOEditor] outgoing saveChanges suppressed (crash state)'
              );
              return;
            }
            // DIAGNOSTIC: dump every outbound saveChanges so we can
            // compare what user1 emits vs what user2 receives and tries
            // to apply in its history replay.
            try {
              const changes = (message as { changes?: unknown }).changes;
              const arr = Array.isArray(changes) ? changes : [];
              console.log('[OOEditor:send] saveChanges', {
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
              });
            } catch {
              /* ignore */
            }
            relayRef.current?.sendSaveChanges(message);
            // Append to our local chain so a future joiner asking for
            // state receives our complete edit history since baseBin.
            // The broadcast went out over the relay for live peers;
            // this is the local copy for lazy catch-up.
            chainRef.current.push(message);
            // Leader-side size monitoring: when the chain gets too
            // big, snapshot the current OO state and broadcast it as
            // the new baseBin. All peers (including us) destroy and
            // recreate their OO against that bin, reset chain. Only
            // the leader triggers to avoid a stampede.
            try {
              if (isSaveLeaderRef.current()) {
                const serialized = JSON.stringify(chainRef.current);
                if (serialized.length > CHECKPOINT_CHAIN_SIZE_BYTES) {
                  const innerWindow = (
                    document.querySelector(
                      'iframe[name="frameEditor"]',
                    ) as HTMLIFrameElement | null
                  )?.contentWindow as any;
                  const innerEditor =
                    innerWindow?.editor || innerWindow?.editorCell;
                  const raw = innerEditor?.asc_nativeGetFile?.();
                  const newBaseBin =
                    typeof raw === 'string'
                      ? raw
                      : raw
                        ? new TextDecoder().decode(raw)
                        : null;
                  if (newBaseBin) {
                    console.log(
                      '[OOEditor] chain size',
                      serialized.length,
                      '> threshold — broadcasting checkpoint reload',
                    );
                    void relayRef.current
                      ?.sendCheckpointReload(newBaseBin)
                      .catch(e => {
                        console.warn(
                          '[OOEditor] sendCheckpointReload failed',
                          e,
                        );
                      });
                  }
                }
              }
            } catch (e) {
              console.warn(
                '[OOEditor] checkpoint-size check threw',
                e,
              );
            }
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
          onForceSaveRequest: () => {
            // Cmd+S / OO-internal forceSave. In production this is a
            // no-op — OO's Save UI is hidden (`forcesave: false`) so
            // the only way to get here is the keyboard shortcut, and
            // users shouldn't need it: our checkpointing layer auto-
            // saves on a timer and on tab close. In development we
            // still route it to `forceSave()` so we don't have to
            // wait 30 s for the auto-tick while testing.
            if (process.env.NODE_ENV !== 'development') return;
            if (outgoingSilencedRef.current) return;
            console.log('[OOEditor] dev Cmd+S → forceSave()');
            forceSave().catch(e => {
              console.warn('[OOEditor] forceSave from Cmd+S failed', e);
            });
          },
        });
        editor.connectMockServer(callbacks);

        // Initialize auto-save — readers don't save
        console.log(
          '[checkpoint] init gate — canEdit:',
          canEdit,
          'abilities:',
          item.abilities
        );
        if (canEdit)
          initCheckpointing({
            editor,
            format: x2tExtension,
            type: x2tType,
            userId: user.sub!,
            onUpload: uploadEncrypted,
            isSaveLeader: () => isSaveLeaderRef.current(),
            onSaveResult: result => {
              // `null` = the most recent save succeeded → clear any
              // banner. Otherwise show the classified error.
              console.log('[OOEditor] onSaveResult', result);
              setSaveError(result);
              if (!result) setSaveRetrying(false);
            },
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
      // React unmounts the JSX subtree (including the iframe
      // placeholder) BEFORE this cleanup runs, so by the time we
      // get here `asc_nativeGetFile` has nothing to read. Calling
      // `forceSave` would just log a misleading "starting save…"
      // followed by "inner editor not available — save did not
      // run". The real save paths are:
      //   - `beforeunload` / `visibilitychange:hidden` (handlers
      //     above) — fire while the iframe is still alive on
      //     genuine tab close / refresh.
      //   - the auto-save interval (every 30s) — safety net for
      //     in-app navigation, where neither of the above fires.
      // If the leader navigates away within 30s of typing, those
      // changes are lost. A cleaner fix would hook Next.js
      // `routeChangeStart` to flush before unmount; not done here.
      if (isSaveLeaderRef.current() && hasUnsavedChanges()) {
        console.warn(
          '[OOEditor] cleanup with unsaved leader changes — last auto-save tick is the only persisted state',
        );
      }
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
    // Users who were invited at a time when they had a DIFFERENT public
    // key (e.g. they reset their vault and re-onboarded) — the wrapped
    // symmetric key was encrypted against their old key, so vault
    // decryption aborts with "wrong secret key for the given ciphertext".
    // Surface the shared key-mismatch panel (also used by the non-office
    // viewer) so the user sees a specific, actionable explanation and
    // their current key's fingerprint, rather than the generic failure.
    const isKeyMismatch =
      !!error && /wrong secret key/i.test(error);
    if (isKeyMismatch) {
      return (
        <KeyMismatchPanel
          shareTimeFingerprint={
            item.encryption_public_key_fingerprint_for_user
          }
        />
      );
    }

    const isNoKeysError =
      !!error && /no key pair|hasKeys|key pair found/i.test(error);
    const isConversionError =
      !!error && /failed to convert|conversion/i.test(error);
    const isPeerStateUnavailable =
      !!error && /PEER_STATE_UNAVAILABLE/.test(error);
    const isRelayUnavailable =
      !!error && /RELAY_UNAVAILABLE/.test(error);
    // `isUnsafeToOpen` is the union — both states share the same
    // retry / read-only escape hatch in the overlay below.
    const isUnsafeToOpen = isPeerStateUnavailable || isRelayUnavailable;
    const isOdfFormat = ['odt', 'ods', 'odp'].includes(x2tExtension);

    const headline = isNoKeysError
      ? t('explorer.encrypted.no_keys_headline', 'Encryption keys required')
      : isRelayUnavailable
        ? t(
            'explorer.encrypted.relay_unavailable_headline',
            'Could not reach the collaboration server',
          )
        : isPeerStateUnavailable
          ? t(
              'explorer.encrypted.peer_state_unavailable_headline',
              'Could not synchronise with the active editor',
            )
          : t('explorer.encrypted.editor_error', 'Failed to load editor');
    const body = isNoKeysError
      ? t(
          'explorer.encrypted.no_keys_body',
          "You don't have an encryption key pair set up for your account yet. Generate or restore your encryption keys from your profile menu, then reopen this document."
        )
      : isRelayUnavailable
        ? t(
            'explorer.encrypted.relay_unavailable_body',
            "We couldn't connect to the collaboration server, so we can't tell whether someone else is currently editing this document. Opening it anyway could overwrite their changes. Please check your network and try again in a few moments, or contact support if the problem persists.",
          )
        : isPeerStateUnavailable
          ? t(
              'explorer.encrypted.peer_state_unavailable_body',
              "Another user is already editing this document. We tried to fetch their live state to join the session safely, but they didn't respond. Opening the document anyway could corrupt it. Please try again in a few moments, or contact support if the problem persists.",
            )
          : error;

    const canEdit = !!item.abilities?.partial_update;
    const canRemoveEncryption = !!item.abilities?.remove_encryption;

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
          maxWidth: '620px',
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
          {isNoKeysError
            ? 'lock'
            : isRelayUnavailable
              ? 'cloud_off'
              : isPeerStateUnavailable
                ? 'sync_problem'
                : 'error'}
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

        {isUnsafeToOpen && (
          <div
            style={{
              display: 'flex',
              gap: '12px',
              flexWrap: 'wrap',
              justifyContent: 'center',
            }}
          >
            <button
              type="button"
              onClick={() => {
                // Retry the live session: clear the override (we
                // want a real relay handshake this time), wipe any
                // stale peer dump bookkeeping, reset the state
                // machine, and bump `reinitKey` so the useEffect
                // tears down and re-runs init from scratch.
                setViewOnlyOverride(false);
                peerStateDumpRef.current = null;
                awaitingPeerStateRef.current = false;
                setError(null);
                setState('loading');
                setReinitKey(k => k + 1);
              }}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 20px',
                fontSize: '14px',
                fontWeight: 500,
                border:
                  '1px solid var(--c--theme--colors--primary-600, #1a56db)',
                borderRadius: '6px',
                background: 'var(--c--theme--colors--primary-600, #1a56db)',
                color: 'var(--c--theme--colors--greyscale-000, #fff)',
                cursor: 'pointer',
              }}
            >
              <span className="material-icons" style={{ fontSize: '18px' }}>
                refresh
              </span>
              {t(
                'explorer.encrypted.peer_state_unavailable_retry',
                'Try again',
              )}
            </button>
            <button
              type="button"
              onClick={() => {
                // Open locally in view-only mode: don't even connect
                // to the relay (we won't see live edits, but we also
                // can't corrupt the active session). Clearing error +
                // bumping `reinitKey` re-runs init with the override
                // on; `canEdit` collapses to false, the relay-setup
                // branch is skipped, and OO boots in `mode:'view'`.
                setViewOnlyOverride(true);
                peerStateDumpRef.current = null;
                awaitingPeerStateRef.current = false;
                setError(null);
                setState('loading');
                setReinitKey(k => k + 1);
              }}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 20px',
                fontSize: '14px',
                fontWeight: 500,
                border:
                  '1px solid var(--c--theme--colors--greyscale-400, #ccc)',
                borderRadius: '6px',
                background: 'var(--c--theme--colors--greyscale-000, #fff)',
                color: 'var(--c--theme--colors--greyscale-800, #222)',
                cursor: 'pointer',
              }}
            >
              <span className="material-icons" style={{ fontSize: '18px' }}>
                visibility
              </span>
              {t(
                'explorer.encrypted.peer_state_unavailable_view_only',
                'Open in read-only',
              )}
            </button>
          </div>
        )}

        {isConversionError && isOdfFormat && (
          <>
            <div
              role="alert"
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '14px 18px',
                background: 'var(--c--theme--colors--warning-100, #fff4e5)',
                border:
                  '1px solid var(--c--theme--colors--warning-400, #e0a84f)',
                borderRadius: '8px',
                textAlign: 'left',
                lineHeight: 1.55,
                fontSize: '14px',
                color: 'var(--c--theme--colors--warning-800, #7a4d00)',
              }}
            >
              <span
                className="material-icons"
                style={{
                  fontSize: '22px',
                  marginTop: '1px',
                  flexShrink: 0,
                }}
              >
                info
              </span>
              <div>
                <strong style={{ display: 'block', marginBottom: '6px' }}>
                  {t(
                    'explorer.encrypted.conversion_hint_title',
                    'Why does this happen?'
                  )}
                </strong>
                {t(
                  'explorer.encrypted.conversion_odf_body',
                  'Encrypted documents are opened with a lightweight browser-based editor that does not support all features available in non-encrypted mode. SmartArt elements are known to prevent ODF files (.odt, .ods, .odp) from loading in this mode.'
                )}
                <br />
                <br />
                {canEdit
                  ? t(
                      'explorer.encrypted.conversion_odf_actions',
                      'You can download the file to remove any SmartArt elements, then re-upload it. Alternatively, you can remove encryption from this document so it opens with the full-featured editor. If the issue persists after removing SmartArt, please contact the technical team to investigate.'
                    )
                  : t(
                      'explorer.encrypted.conversion_odf_no_edit',
                      'Please contact the owner of this document or a user with editing rights so they can remove the SmartArt elements or remove encryption from the file. If the issue persists after removing SmartArt, please contact the technical team to investigate.'
                    )}
              </div>
            </div>

            {canEdit && (
              <div
                style={{
                  display: 'flex',
                  gap: '12px',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                }}
              >
                <button
                  type="button"
                  disabled={downloading}
                  onClick={async () => {
                    setDownloading(true);
                    try {
                      await downloadDecryptedFile(item);
                    } catch (e) {
                      console.error('[OOEditor] download decrypted failed', e);
                    } finally {
                      setDownloading(false);
                    }
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 20px',
                    fontSize: '14px',
                    fontWeight: 500,
                    border:
                      '1px solid var(--c--theme--colors--greyscale-400, #ccc)',
                    borderRadius: '6px',
                    background: 'var(--c--theme--colors--greyscale-000, #fff)',
                    color: 'var(--c--theme--colors--greyscale-800, #222)',
                    cursor: downloading ? 'wait' : 'pointer',
                    opacity: downloading ? 0.6 : 1,
                  }}
                >
                  <span className="material-icons" style={{ fontSize: '18px' }}>
                    download
                  </span>
                  {downloading
                    ? t('explorer.encrypted.downloading', 'Downloading...')
                    : t(
                        'explorer.encrypted.download_to_inspect',
                        'Download file'
                      )}
                </button>

                {canRemoveEncryption && (
                  <button
                    type="button"
                    onClick={() => setShowRemoveEncryption(true)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '10px 20px',
                      fontSize: '14px',
                      fontWeight: 500,
                      border: 'none',
                      borderRadius: '6px',
                      background:
                        'var(--c--theme--colors--primary-600, #0056b3)',
                      color: '#fff',
                      cursor: 'pointer',
                    }}
                  >
                    <span
                      className="material-icons"
                      style={{ fontSize: '18px' }}
                    >
                      lock_open
                    </span>
                    {t(
                      'explorer.encrypted.remove_encryption',
                      'Remove encryption'
                    )}
                  </button>
                )}
              </div>
            )}

            {showRemoveEncryption && (
              <ModalRecursiveRemoveEncryption
                isOpen={showRemoveEncryption}
                onClose={() => setShowRemoveEncryption(false)}
                item={item}
              />
            )}
          </>
        )}

        {isConversionError && !isOdfFormat && (
          <>
            <p
              style={{
                margin: 0,
                fontSize: '14px',
                lineHeight: 1.5,
                color: 'var(--c--theme--colors--greyscale-600, #666)',
              }}
            >
              {t(
                'explorer.encrypted.conversion_unexpected',
                'This error is unexpected for this file format. You can download the file to inspect it, or try removing encryption — the full-featured editor may be able to open it. If removing encryption works, please contact the technical team so they can investigate why the encrypted editor failed.'
              )}
            </p>

            {canEdit && (
              <div
                style={{
                  display: 'flex',
                  gap: '12px',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                }}
              >
                <button
                  type="button"
                  disabled={downloading}
                  onClick={async () => {
                    setDownloading(true);
                    try {
                      await downloadDecryptedFile(item);
                    } catch (e) {
                      console.error('[OOEditor] download decrypted failed', e);
                    } finally {
                      setDownloading(false);
                    }
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 20px',
                    fontSize: '14px',
                    fontWeight: 500,
                    border:
                      '1px solid var(--c--theme--colors--greyscale-400, #ccc)',
                    borderRadius: '6px',
                    background: 'var(--c--theme--colors--greyscale-000, #fff)',
                    color: 'var(--c--theme--colors--greyscale-800, #222)',
                    cursor: downloading ? 'wait' : 'pointer',
                    opacity: downloading ? 0.6 : 1,
                  }}
                >
                  <span className="material-icons" style={{ fontSize: '18px' }}>
                    download
                  </span>
                  {downloading
                    ? t('explorer.encrypted.downloading', 'Downloading...')
                    : t(
                        'explorer.encrypted.download_to_inspect',
                        'Download file'
                      )}
                </button>

                {canRemoveEncryption && (
                  <button
                    type="button"
                    onClick={() => setShowRemoveEncryption(true)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '10px 20px',
                      fontSize: '14px',
                      fontWeight: 500,
                      border: 'none',
                      borderRadius: '6px',
                      background:
                        'var(--c--theme--colors--primary-600, #0056b3)',
                      color: '#fff',
                      cursor: 'pointer',
                    }}
                  >
                    <span
                      className="material-icons"
                      style={{ fontSize: '18px' }}
                    >
                      lock_open
                    </span>
                    {t(
                      'explorer.encrypted.remove_encryption',
                      'Remove encryption'
                    )}
                  </button>
                )}
              </div>
            )}

            {!canEdit && (
              <p
                style={{
                  margin: 0,
                  fontSize: '14px',
                  lineHeight: 1.5,
                  color: 'var(--c--theme--colors--greyscale-600, #666)',
                }}
              >
                {t(
                  'explorer.encrypted.conversion_unexpected_no_edit',
                  'Please contact the owner of this document or a user with editing rights to investigate.'
                )}
              </p>
            )}

            {showRemoveEncryption && (
              <ModalRecursiveRemoveEncryption
                isOpen={showRemoveEncryption}
                onClose={() => setShowRemoveEncryption(false)}
                item={item}
              />
            )}
          </>
        )}
      </div>
    );
  }

  return (
    <div ref={containerRef} className={styles.ooEditorContainer}>
      {/* Save-error banner. Static block — lives above the editor
          area and reduces the iframe height, so the OO toolbar and
          content stay fully usable while the banner is up. */}
      {saveError && state !== 'oo-crashed' && (
        <div
          role="alert"
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
            padding: '10px 16px',
            background:
              saveError.kind === 'fatal'
                ? 'var(--c--theme--colors--danger-100, #fde8e8)'
                : 'var(--c--theme--colors--warning-100, #fff4e5)',
            borderBottom:
              saveError.kind === 'fatal'
                ? '1px solid var(--c--theme--colors--danger-400, #e66)'
                : '1px solid var(--c--theme--colors--warning-400, #e0a84f)',
            color:
              saveError.kind === 'fatal'
                ? 'var(--c--theme--colors--danger-800, #800)'
                : 'var(--c--theme--colors--warning-800, #7a4d00)',
            fontSize: '13px',
            flexShrink: 0,
          }}
        >
          <span
            className="material-icons"
            style={{ fontSize: '20px', flexShrink: 0 }}
            aria-hidden
          >
            {saveError.kind === 'fatal' ? 'error' : 'sync_problem'}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <strong style={{ display: 'block', marginBottom: 2 }}>
              {saveError.kind === 'fatal'
                ? t(
                    'explorer.encrypted.save_error_fatal_title',
                    'Saving failed — please contact support'
                  )
                : t(
                    'explorer.encrypted.save_error_transient_title',
                    'Sync error — save will be retried'
                  )}
            </strong>
            <span
              style={{
                display: 'block',
                fontSize: '12px',
                opacity: 0.85,
                lineHeight: 1.4,
                wordBreak: 'break-word',
              }}
            >
              {saveError.kind === 'fatal'
                ? t(
                    'explorer.encrypted.save_error_fatal_body',
                    'The document contains content we cannot serialize to ' +
                      'the on-disk format (often a chart). ' +
                      'Your recent edits are visible but unsaved. Please ' +
                      'undo the last change or contact support. Details: '
                  )
                : t(
                    'explorer.encrypted.save_error_transient_body',
                    'We could not upload the latest save. Details: '
                  )}
              {saveError.detail}
            </span>
          </div>
          {saveError.kind === 'transient' && (
            <button
              type="button"
              disabled={saveRetrying}
              onClick={async () => {
                setSaveRetrying(true);
                try {
                  await forceSave();
                } catch {
                  /* onSaveResult will surface the updated state */
                } finally {
                  setSaveRetrying(false);
                }
              }}
              style={{
                flexShrink: 0,
                padding: '6px 14px',
                border: '1px solid currentColor',
                borderRadius: '4px',
                background: 'transparent',
                color: 'inherit',
                fontSize: '12px',
                fontWeight: 600,
                cursor: saveRetrying ? 'wait' : 'pointer',
              }}
            >
              {saveRetrying
                ? t('explorer.encrypted.save_error_retrying', 'Retrying…')
                : t('explorer.encrypted.save_error_retry', 'Retry now')}
            </button>
          )}
        </div>
      )}
      <div className={styles.editorArea}>
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
            <span
              style={{ color: 'var(--c--theme--colors--greyscale-600, #666)' }}
            >
              {state === 'decrypting' &&
                t('explorer.encrypted.decrypting', 'Decrypting...')}
              {state === 'converting' &&
                t('explorer.encrypted.converting', 'Preparing editor...')}
              {state === 'syncing-history' &&
                t(
                  'explorer.encrypted.syncing_history',
                  'Syncing collaborative state...'
                )}
              {state === 'stale-resyncing' &&
                t(
                  'explorer.encrypted.stale_resyncing',
                  'Reconnecting after long disconnect — refetching document...'
                )}
              {state === 'peer-resyncing' &&
                t(
                  'explorer.encrypted.peer_resyncing',
                  'A co-editor is resyncing — holding on for a moment...'
                )}
              {(state === 'loading' || state === 'mounting') &&
                t('explorer.encrypted.loading_editor', 'Loading editor...')}
            </span>
          </div>
        )}
        {/* Flush-on-close overlay: covers the editor while we run the
            final save kicked off by the parent's close-button guard.
            zIndex above the loading overlay so it wins if both are
            true (shouldn't happen — the editor is always 'ready' by
            the time the user can click close — but defend anyway). */}
        {flushingOnClose && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '16px',
              background: 'rgba(255, 255, 255, 0.95)',
              zIndex: 20,
            }}
          >
            <Loader />
            <span
              style={{
                color: 'var(--c--theme--colors--greyscale-700, #444)',
                fontSize: '15px',
              }}
            >
              {t(
                'explorer.encrypted.flushing_on_close',
                'Saving your changes before closing…',
              )}
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
                'Synchronization error'
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
                  'editor to fetch the latest saved state.'
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
                    'Waiting for peers to save…'
                  )
                : t('explorer.encrypted.oo_crashed_reload', 'Reload editor')}
            </button>
            <style>
              {
                '@keyframes oo-crashed-spin { to { transform: rotate(360deg); } }'
              }
            </style>
          </div>
        )}
      </div>
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
