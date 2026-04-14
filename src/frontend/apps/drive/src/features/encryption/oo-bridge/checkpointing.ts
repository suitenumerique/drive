/**
 * Checkpointing: periodic save of the document to Drive's S3.
 *
 * Extracts the current document as binary from OnlyOffice,
 * converts back to the original format (docx/xlsx/pptx),
 * encrypts via the vault, and uploads to S3.
 */

import { convertFromInternal } from './x2tConverter';
import { getPatchIndex } from './changesPipeline';
import { acquireSaveLock, releaseSaveLock, isSaveLocked } from './locks';
import { pauseIncomingOT, resumeIncomingOT } from './incomingOtGate';

const CHECKPOINT_CHANGES_THRESHOLD = 50;
const CHECKPOINT_TIME_INTERVAL_MS = 15_000; // 15 seconds for testing

/** Reference to the OnlyOffice editor instance */
let editorInstance: any = null;

/** Original file format (e.g. "docx") */
let originalFormat: string = '';

/** Document type for x2t (e.g. "doc", "sheet", "presentation") */
let documentType: string = '';

/** Last checkpoint patch index */
let lastCheckpointIndex = 0;

/** Last checkpoint timestamp */
let lastCheckpointTime = Date.now();

/** Current user ID for save lock */
let currentUserId: string = '';

/** Whether a save is currently in progress */
let isSaving = false;

/** Auto-save interval timer */
let autoSaveTimer: ReturnType<typeof setInterval> | null = null;

/** Callback for uploading encrypted content */
let uploadCallback:
  | ((
      content: ArrayBuffer,
      format: string,
      epochMs: number,
    ) => Promise<void>)
  | null = null;

/**
 * Initialize the checkpointing system.
 */


/** Callback to check if this client is the save leader (first joiner saves) */
let isSaveLeader: (() => boolean) | null = null;

export function initCheckpointing(opts: {
  editor: any;
  format: string;
  type: string;
  userId: string;
  onUpload: (
    content: ArrayBuffer,
    format: string,
    epochMs: number,
  ) => Promise<void>;
  /** Return true if this client should be responsible for saving.
   *  When absent, all clients save (single-user mode). */
  isSaveLeader?: () => boolean;
}): void {
  editorInstance = opts.editor;
  originalFormat = opts.format;
  documentType = opts.type;
  currentUserId = opts.userId;
  uploadCallback = opts.onUpload;
  isSaveLeader = opts.isSaveLeader ?? null;
  lastCheckpointIndex = getPatchIndex();
  lastCheckpointTime = Date.now();

  if (autoSaveTimer) clearInterval(autoSaveTimer);
  autoSaveTimer = setInterval(() => {
    checkAndSave();
  }, CHECKPOINT_TIME_INTERVAL_MS);
  console.log(
    '[checkpoint] initialised — interval:',
    CHECKPOINT_TIME_INTERVAL_MS,
    'ms format:',
    originalFormat,
    'type:',
    documentType,
  );
}

/**
 * Stop the checkpointing system.
 */
export function stopCheckpointing(): void {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer);
    autoSaveTimer = null;
  }
}

/**
 * Check if a checkpoint is needed and trigger one if so.
 */
export async function checkAndSave(): Promise<void> {
  const currentIndex = getPatchIndex();
  const changesSinceCheckpoint = currentIndex - lastCheckpointIndex;
  const timeSinceCheckpoint = Date.now() - lastCheckpointTime;

  const shouldSave =
    changesSinceCheckpoint >= CHECKPOINT_CHANGES_THRESHOLD ||
    (changesSinceCheckpoint > 0 &&
      timeSinceCheckpoint >= CHECKPOINT_TIME_INTERVAL_MS);

  const amLeader = isSaveLeader ? isSaveLeader() : true;
  console.log(
    '[checkpoint] tick',
    'changes:',
    changesSinceCheckpoint,
    'msSince:',
    timeSinceCheckpoint,
    'shouldSave:',
    shouldSave,
    'isSaving:',
    isSaving,
    'leader:',
    amLeader,
  );
  if (shouldSave && !isSaving && amLeader) {
    await saveCheckpoint();
  }
}

/**
 * Check if there are changes that haven't been saved yet.
 */
export function hasUnsavedChanges(): boolean {
  return getPatchIndex() > lastCheckpointIndex;
}

/**
 * Force a save (e.g. when user closes the editor).
 */
export async function forceSave(): Promise<void> {
  if (isSaving) return;
  const currentIndex = getPatchIndex();
  if (currentIndex > lastCheckpointIndex) {
    await saveCheckpoint();
  }
}

/**
 * Extract the document from OnlyOffice, convert to original format,
 * and call the upload callback.
 */
async function saveCheckpoint(): Promise<void> {
  if (!editorInstance || !uploadCallback) return;
  if (isSaving) return;

  // Try to acquire save lock (only one user can save at a time)
  if (!acquireSaveLock(currentUserId)) {
    console.log('[checkpoint] skipped: another user holds the save lock');
    return;
  }

  isSaving = true;
  console.log('[checkpoint] starting save…');

  try {
    // Extract current document as binary from OnlyOffice
    // asc_nativeGetFile() is on the INNER editor object inside the OO iframe,
    // not on the DocsAPI.DocEditor wrapper. Access it via the iframe's window.
    const ooIframe = document.querySelector('iframe[name="frameEditor"]') as HTMLIFrameElement | null;
    const innerWindow = ooIframe?.contentWindow as any;
    const innerEditor = innerWindow?.editor || innerWindow?.editorCell;

    if (!innerEditor?.asc_nativeGetFile) {
      console.warn('Checkpoint: inner editor not available yet, skipping');
      return;
    }

    // Capture the snapshot epoch and extract the native binary under the
    // incoming-OT gate so no remote change can be applied between the two
    // operations. Any remote change that arrives during this window is
    // queued and drained after we release — those events have a relay
    // timestamp > epochMs and will be replayed on joiners as "post-snapshot".
    let rawBin: unknown;
    let epochMs: number;
    pauseIncomingOT();
    try {
      epochMs = Date.now();
      rawBin = innerEditor.asc_nativeGetFile();
    } finally {
      resumeIncomingOT();
    }

    if (!rawBin) {
      console.warn('Checkpoint: empty document, skipping save');
      return;
    }

    // asc_nativeGetFile() returns OO's native format as a string:
    // "DOCY;v5;{size};{base64data}" (word), "XLSY;..." (sheet), "PPTY;..." (slide)
    // x2t reads this format directly — pass the raw string, not decoded bytes.
    // We encode it as UTF-8 bytes for the WASM filesystem.
    let binBuffer: ArrayBuffer;
    if (typeof rawBin === 'string') {
      const encoder = new TextEncoder();
      binBuffer = encoder.encode(rawBin).buffer;
    } else if (rawBin instanceof ArrayBuffer) {
      binBuffer = rawBin;
    } else {
      binBuffer = (rawBin as { buffer: ArrayBuffer }).buffer;
    }

    if (binBuffer.byteLength === 0) {
      console.warn('Checkpoint: empty document, skipping save');
      return;
    }

    // Gather every image registered in OO's document urls and write them
    // into x2t's /working/media/ before conversion — without this, x2t can't
    // find the bytes for inserted images and produces a broken/empty file.
    const media = new Map<string, Uint8Array>();
    try {
      const urls =
        innerWindow?.AscCommon?.g_oDocumentUrls?.getUrls?.() ?? {};
      await Promise.all(
        Object.entries(urls).map(async ([key, value]) => {
          if (typeof value !== 'string') return;
          try {
            const resp = await fetch(value);
            if (!resp.ok) return;
            const bytes = new Uint8Array(await resp.arrayBuffer());
            const name = key.startsWith('media/')
              ? key.slice('media/'.length)
              : key;
            media.set(name, bytes);
          } catch {
            /* skip missing image */
          }
        }),
      );
    } catch {
      /* g_oDocumentUrls unavailable */
    }

    const converted = await convertFromInternal(
      binBuffer,
      originalFormat,
      documentType,
      media,
    );

    const convertedBytes = converted.byteLength;
    if (convertedBytes === 0) {
      // SAFETY: never overwrite S3 with empty bytes — that destroys the doc.
      console.warn(
        '[checkpoint] conversion produced 0 bytes — refusing to upload (this would wipe the file)',
      );
      return;
    }

    // Upload (encryption happens in the callback). Note that the vault
    // transfers the buffer into a worker, so `converted.buffer` is detached
    // after this await — read the byte count from the local capture above.
    await uploadCallback(converted.buffer, originalFormat, epochMs);

    lastCheckpointIndex = getPatchIndex();
    lastCheckpointTime = Date.now();
    console.log(
      '[checkpoint] save complete — uploaded',
      convertedBytes,
      'bytes as',
      originalFormat,
      '(images:',
      media.size,
      ', epochMs:',
      epochMs,
      ')',
    );
  } catch (error) {
    console.error('[checkpoint] save failed:', error);
  } finally {
    isSaving = false;
    releaseSaveLock(currentUserId);
  }
}
