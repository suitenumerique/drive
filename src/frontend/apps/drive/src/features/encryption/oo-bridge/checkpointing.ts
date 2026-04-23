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
import { injectDriveBin } from './odtBundle';

const CHECKPOINT_CHANGES_THRESHOLD = 50;
const CHECKPOINT_TIME_INTERVAL_MS = 30_000; // 30 seconds for testing

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
 * Save-result notification. Called with `null` on success, or with a
 * classified error on failure:
 *  - `fatal`: x2t refused to serialize the document (e.g. an OLE
 *    embed the writer can't handle). Retrying will keep failing
 *    until the user removes the offending content — so the overlay
 *    should tell them to contact support / roll back.
 *  - `transient`: extract or upload step failed (innerEditor not
 *    ready, S3 network error, vault encrypt failure). The next
 *    auto-save tick will likely succeed; the overlay should invite
 *    a manual retry and auto-clear on the next success.
 */
let saveResultCallback:
  | ((result: { kind: 'fatal' | 'transient'; detail: string } | null) => void)
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
  /** Notified on every save attempt outcome (see `saveResultCallback`). */
  onSaveResult?: (
    result: { kind: 'fatal' | 'transient'; detail: string } | null,
  ) => void;
}): void {
  editorInstance = opts.editor;
  originalFormat = opts.format;
  documentType = opts.type;
  currentUserId = opts.userId;
  uploadCallback = opts.onUpload;
  saveResultCallback = opts.onSaveResult ?? null;
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
 * Called on non-leader peers when they observe a remote `save:committed`
 * event. Marks the local `lastCheckpointIndex` as up-to-date so the
 * beforeunload guard doesn't show the "unsaved changes" confirm on a
 * peer that has no pending local work of its own.
 */
export function markRemoteSaveCommitted(): void {
  lastCheckpointIndex = getPatchIndex();
  lastCheckpointTime = Date.now();
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

  // Separate error classes for the overlay:
  //  - conversionFailure: x2t refused the document. The user has to
  //    remove the offending content (OLE embed, broken chart, …).
  //  - transientFailure: the extract or upload step hit a recoverable
  //    error — the next save will probably succeed.
  let conversionFailure: string | null = null;
  let transientFailure: string | null = null;

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
      // DIAGNOSTIC: dump the URL-registry keys so we can tell whether
      // "images: N" reflects real user-added attachments or just OO's
      // internal template/theme entries.
      console.log('[checkpoint] g_oDocumentUrls keys:', Object.keys(urls));
      await Promise.all(
        Object.entries(urls).map(async ([key, value]) => {
          if (typeof value !== 'string') return;
          // Only entries under the `media/` prefix are real attachments.
          // OO also registers internal artefacts here (e.g. `Editor.bin`,
          // the serialized sdkjs document state) which must NOT be fed
          // to x2t as media — doing so either corrupts the output or
          // bloats the exported file.
          if (!key.startsWith('media/')) return;
          try {
            const resp = await fetch(value);
            if (!resp.ok) return;
            const bytes = new Uint8Array(await resp.arrayBuffer());
            const name = key.slice('media/'.length);
            media.set(name, bytes);
          } catch {
            /* skip missing image */
          }
        }),
      );
    } catch {
      /* g_oDocumentUrls unavailable */
    }

    // Phase 1: x2t conversion. A throw here means the document
    // contains content the writer can't serialize — retrying will
    // keep failing, so classify as fatal.
    let converted: Uint8Array;
    try {
      converted = await convertFromInternal(
        binBuffer,
        originalFormat,
        documentType,
        media,
      );
    } catch (error) {
      conversionFailure =
        error instanceof Error ? error.message : String(error);
      console.error('[checkpoint] conversion failed:', error);
      return;
    }

    const convertedBytes = converted.byteLength;
    if (convertedBytes === 0) {
      // SAFETY: never overwrite S3 with empty bytes — that destroys the doc.
      // Treat as fatal: x2t produced nothing, retrying won't help.
      console.warn(
        '[checkpoint] conversion produced 0 bytes — refusing to upload (this would wipe the file)',
      );
      conversionFailure = 'x2t conversion produced 0 bytes';
      return;
    }

    // Embed OO's native state as a sidecar inside the archive so the
    // next Drive open can restore the exact same internal object ids.
    // Without this, every reload regenerates ids from a pure counter
    // and diverges from peers still running their original session
    // (silent OT drop or `undefined.Set_*` crash in Apply_Data).
    // External tools (LibreOffice, Word) ignore the `.drive/` entry.
    // Media bytes are NOT stored here — `asc_nativeGetFile()` emits
    // structure only, images stay in `Pictures/` as usual and are
    // resolved at load via `g_oDocumentUrls`.
    let bundled: Uint8Array;
    try {
      const binString =
        typeof rawBin === 'string'
          ? rawBin
          : new TextDecoder().decode(binBuffer);
      bundled = injectDriveBin(converted, binString);
      console.log(
        '[checkpoint] bundled sidecar .drive/editor.bin',
        'binSize:', binString.length,
        'odtSize:', convertedBytes,
        'finalSize:', bundled.byteLength,
      );
    } catch (e) {
      // Fall back to plain ODT upload if the ZIP rewrite fails — we
      // must never abandon a save: the .odt without a sidecar is
      // still a fully valid rendered document, only the id-preservation
      // optimisation is lost.
      console.warn(
        '[checkpoint] sidecar injection failed — uploading plain ODT',
        e,
      );
      bundled = converted;
    }

    // Phase 2: encrypt + upload. A throw here is almost always
    // transient (S3 network error, presigned URL refresh, vault
    // worker race). Note the vault worker transfers the buffer, so
    // `bundled.buffer` is detached after the await — read the
    // byte count from the local capture above.
    try {
      await uploadCallback(bundled.buffer, originalFormat, epochMs);
    } catch (error) {
      transientFailure =
        error instanceof Error ? error.message : String(error);
      console.error('[checkpoint] upload failed:', error);
      return;
    }

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
    // Anything thrown outside the inner try/catches (extract step,
    // pause/resume gate, etc.) is classified transient — the next
    // tick may find the editor in a better state.
    transientFailure =
      error instanceof Error ? error.message : String(error);
    console.error('[checkpoint] save failed:', error);
  } finally {
    isSaving = false;
    releaseSaveLock(currentUserId);
    if (conversionFailure) {
      saveResultCallback?.({ kind: 'fatal', detail: conversionFailure });
    } else if (transientFailure) {
      saveResultCallback?.({ kind: 'transient', detail: transientFailure });
    } else {
      // Clears any previously-shown error overlay.
      saveResultCallback?.(null);
    }
  }
}
