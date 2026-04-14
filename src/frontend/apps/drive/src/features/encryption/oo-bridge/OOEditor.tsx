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
import { convertToInternal, convertFromInternal } from './x2tConverter';
import { createMockServerCallbacks, sendToEditor, setEditorInstance } from './mockServer';
import {
  initLocalUser,
  getUniqueOOId,
  addRemoteUser,
  removeRemoteUser,
  buildConnectStateMessage,
  getRemoteOOInternalId,
} from './participants';
import { resetPatchIndex, handleIncomingChanges } from './changesPipeline';
import { EncryptedRelay } from './encryptedRelay';
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
} from './checkpointing';
import {
  MIME_TO_DOC_TYPE,
  MIME_TO_OO_FILE_TYPE,
  MIME_TO_X2T_TYPE,
  MIME_TO_EXTENSION,
  type OOConfig,
  type OOChange,
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

type EditorState = 'loading' | 'decrypting' | 'converting' | 'mounting' | 'ready' | 'error';

export const OOEditor = ({ item }: OOEditorProps) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [state, setState] = useState<EditorState>('loading');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [relayFailed, setRelayFailed] = useState(false);
  const editorRef = useRef<OOEditorInstance | null>(null);
  const relayRef = useRef<EncryptedRelay | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptLoadedRef = useRef(false);
  // Connected peers with edit capability (not including self). Used for save leader election.
  const editorPeersRef = useRef<Set<string>>(new Set());
  // Cached reference to the OO inner editor (lives inside frameEditor iframe).
  // Used to read the local cursor on each keystroke since OO doesn't auto-send
  // it during text insertion.
  const innerEditorRef = useRef<any>(null);
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
    async (content: ArrayBuffer, _format: string): Promise<void> => {
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

      // Encrypt via vault
      const { encryptedData } = await vaultClient.encryptWithKey(
        content,
        entryKeyBytes.buffer,
        encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined
      );

      // Get a presigned S3 upload URL for the existing file key
      // S3 versioning keeps previous versions — no new filename needed
      const urlResponse = await fetchAPI(
        `items/${item.id}/encryption-upload-url/`,
        { method: 'POST' },
        { redirectOn40x: false },
      );
      const { upload_url: uploadUrl } = await urlResponse.json();

      // Upload encrypted content to S3 via presigned URL (XHR like regular Drive uploads)
      const encryptedBytes = new Uint8Array(encryptedData);
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', uploadUrl);
        xhr.setRequestHeader('X-amz-acl', 'private');
        xhr.setRequestHeader('Content-Type', 'application/octet-stream');
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

    },
    [item.id]
  );

  /**
   * Main initialization: decrypt → convert → load editor.
   */
  useEffect(() => {
    let cancelled = false;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges()) {
        e.preventDefault();
      }
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden' && hasUnsavedChanges()) {
        forceSave().catch(() => {});
      }
    };

    const init = async () => {
      try {
        if (!item.url || !user) return;

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

        const { data: decryptedBuffer } = await vaultClient.decryptWithKey(
          encryptedBuffer,
          entryKeyBytes.buffer,
          encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined
        );
        if (cancelled) return;

        // Step 3: Convert to .bin format
        setState('converting');
        const { bin } = await convertToInternal(decryptedBuffer, filename);
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
            },
            permissions: {
              chat: false,
            },
          },
          events: {
            onAppReady: () => {
              // Editor UI is ready
            },
            onDocumentReady: () => {
              setState('ready');
              try {
                const iframe = document.querySelector(
                  'iframe[name="frameEditor"]',
                ) as HTMLIFrameElement | null;
                const innerWin = iframe?.contentWindow as any;
                innerEditorRef.current =
                  innerWin?.Asc?.editor || innerWin?.editor || null;
              } catch {
                /* inner editor not reachable — cursor sync will no-op */
              }
            },
            onError: event => {
              console.error('OnlyOffice error:', event.data);
              setError(String(event.data));
              setState('error');
            },
          },
        };

        if (!window.DocsAPI) {
          throw new Error('OnlyOffice API not loaded');
        }

        // OnlyOffice's connectMockServer expects window.APP to exist
        (window as any).APP = (window as any).APP || {};

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
          onLocalChanges: (changes: OOChange[]) => {
            relayRef.current?.sendChanges(changes);
            // OO doesn't fire its cursor-send path on text insertion (only on
            // mouse/arrow moves), so we read the cursor ourselves from the
            // inner editor and push it through the relay.
            try {
              const cursorBin =
                innerEditorRef.current?.WordControl?.m_oLogicDocument?.History?.Get_DocumentPositionBinary?.();
              if (cursorBin) {
                relayRef.current?.sendCursor(cursorBin);
              }
            } catch {
              /* swallow — cursor sync is best-effort */
            }
          },
          onLockRequest: (type, lockData) => {
            relayRef.current?.sendLock(type, lockData);
          },
          onCursorUpdate: cursor => {
            relayRef.current?.sendCursor(cursor);
          },
          onSaveLockCheck: () => false,
        });
        editor.connectMockServer(callbacks);

        // Initialize auto-save — readers don't save
        if (canEdit) initCheckpointing({
          editor,
          format: x2tExtension,
          type: x2tType,
          userId: user.sub!,
          onUpload: uploadEncrypted,
          // Deterministic leader election: lowest userId among connected EDITORS saves.
          // Every client computes this independently — no coordination needed.
          // Readers never save. If alone (no editor peers), this editor is leader.
          isSaveLeader: () => {
            if (!canEdit) return false;
            const peers = editorPeersRef.current;
            if (peers.size === 0) return true;
            for (const peerId of peers) {
              if (peerId < user!.sub!) return false;
            }
            return true;
          },
        });

        // Listen for tab close/refresh to save or warn
        window.addEventListener('beforeunload', handleBeforeUnload);
        document.addEventListener('visibilitychange', handleVisibilityChange);

        // Set up the encrypted relay for collaboration (optional — PoC works without it)
        try {
          const relay = new EncryptedRelay({
            roomId: item.id,
            userId: user.sub!,
            userName: user.full_name || user.email,
            vaultClient,
            encryptedSymmetricKey: entryKeyBytes.buffer,
            encryptedKeyChain:
              encryptedKeyChain.length > 0 ? encryptedKeyChain : [],
            callbacks: {
              onRemoteChanges: changes => {
                sendToEditor(handleIncomingChanges(changes));
              },
              onPeerJoin: (userId, userName, peerCanEdit) => {
                if (peerCanEdit) editorPeersRef.current.add(userId);
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
                    if (peer.canEdit) editorPeersRef.current.add(peer.userId);
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
                sendToEditor({
                  type: 'getLock',
                  locks: [lockData],
                } as any);
              },
              onCursorUpdate: (userId, cursor) => {
                const senderOOId = getRemoteOOInternalId(userId);
                if (!senderOOId) return;
                const cursorString =
                  typeof cursor === 'string' ? cursor : JSON.stringify(cursor);
                sendToEditor({
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
              },
            },
          });
          relayRef.current = relay;
          relay.connect();
        } catch (relayErr) {
          console.warn('Relay setup failed (single-user mode):', relayErr);
        }

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
      }
    };
  }, [item.id]);

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
      {state !== 'ready' && (
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
            {(state === 'loading' || state === 'mounting') &&
              t('explorer.encrypted.loading_editor', 'Loading editor...')}
          </span>
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
