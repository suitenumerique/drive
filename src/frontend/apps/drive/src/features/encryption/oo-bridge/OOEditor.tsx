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
import { createMockServerCallbacks, sendToEditor, setEditorInstance } from './mockServer';
import {
  initLocalUser,
  getUniqueOOId,
  addRemoteUser,
  removeRemoteUser,
  buildConnectStateMessage,
  getRemoteOOInternalId,
} from './participants';
import { resetPatchIndex } from './changesPipeline';
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
  const editorRef = useRef<OOEditorInstance | null>(null);
  const relayRef = useRef<EncryptedRelay | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptLoadedRef = useRef(false);
  // Connected peers with edit capability (not including self). Used for save leader election.
  const editorPeersRef = useRef<Set<string>>(new Set());
  // Reference to the inner OO iframe's window — used to register media in
  // g_oDocumentUrls when inbound saveChanges envelopes carry inline images.
  const innerWindowRef = useRef<any>(null);
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
              } catch (e) {
                console.warn('[OOEditor] image registration failed', e);
              }
            },
            onDocumentReady: () => {
              setState('ready');
              try {
                const ooIframe = document.querySelector(
                  'iframe[name="frameEditor"]',
                ) as HTMLIFrameElement | null;
                const innerWindow = ooIframe?.contentWindow as any;
                innerWindowRef.current = innerWindow;

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
                // Defensive shields for OO-internal crashes we can't fix at
                // the source. Each one wraps a hot-path method with a
                // try/catch so a bad input doesn't unmount the editor —
                // we log a warning and let the next iteration / event
                // proceed. Idempotent via a per-method flag.
                const shield = (
                  proto: any,
                  method: string,
                  label: string,
                ) => {
                  if (!proto || typeof proto[method] !== 'function') return;
                  const flag = `__driveShielded_${method}`;
                  if (proto[flag]) return;
                  const orig = proto[method];
                  proto[method] = function (...args: unknown[]) {
                    try {
                      return orig.apply(this, args);
                    } catch (e) {
                      console.warn(
                        `[OOEditor] swallowed ${label} error`,
                        e,
                      );
                    }
                  };
                  proto[flag] = true;
                };

                // CDocument.Update_ForeignCursor — Run.GetDocumentPositionFromObject
                // missing when remote cursor references a non-ParaRun.
                shield(
                  innerWindow?.CDocument?.prototype,
                  'Update_ForeignCursor',
                  'Update_ForeignCursor',
                );

                // CGraphicObjects.removeById — oDrawing.isHdrFtrChild missing.
                // CGraphicObjects.updateCursorType — oShape.isForm missing.
                const CGO =
                  innerWindow?.AscFormat?.CGraphicObjects ||
                  innerWindow?.AscCommonWord?.CGraphicObjects;
                shield(CGO?.prototype, 'removeById', 'CGraphicObjects.removeById');
                shield(
                  CGO?.prototype,
                  'updateCursorType',
                  'CGraphicObjects.updateCursorType',
                );

                // CCollaborativeChanges.Apply_Data — individual change
                // class methods (private_UpdateMarksOnSplit etc.) missing.
                // Wrapping at Apply_Data lets the per-change loop in
                // Apply_OtherChanges keep going past one bad change.
                const CCC =
                  innerWindow?.AscCommon?.CCollaborativeChanges;
                shield(
                  CCC?.prototype,
                  'Apply_Data',
                  'CCollaborativeChanges.Apply_Data',
                );

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
            relayRef.current?.sendSaveChanges(message);
          },
          onLockRequest: (type, lockData) => {
            relayRef.current?.sendLock(type, lockData);
          },
          onCursorUpdate: cursor => {
            relayRef.current?.sendCursor(cursor);
          },
          onMessageBroadcast: messages => {
            relayRef.current?.sendMessage(messages);
          },
          onMetaBroadcast: messages => {
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
              onSaveChanges: (_userId, message, media) => {
                // Register any inline media in g_oDocumentUrls BEFORE we
                // hand the change to OO. The change carries image
                // references by name; without the bytes registered first,
                // OO falls back to fetching `<name>` from the editor app
                // dir and 404s.
                if (media) {
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
                sendToEditorGuarded(message as any);
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
              },
              onMessageBroadcast: (_userId, messages) => {
                sendToEditorGuarded({ type: 'message', messages } as any);
              },
              onMetaBroadcast: (_userId, messages) => {
                sendToEditorGuarded({ type: 'meta', messages } as any);
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
