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

const CHECKPOINT_CHANGES_THRESHOLD = 50;
const CHECKPOINT_TIME_INTERVAL_MS = 30_000; // 30 seconds

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
  | ((content: ArrayBuffer, format: string) => Promise<void>)
  | null = null;

/**
 * Initialize the checkpointing system.
 */
/** Callback for broadcasting save lock to peers */
let saveLockBroadcast: ((locked: boolean) => void) | null = null;

export function initCheckpointing(opts: {
  editor: any;
  format: string;
  type: string;
  userId: string;
  onUpload: (content: ArrayBuffer, format: string) => Promise<void>;
  onSaveLock?: (locked: boolean) => void;
}): void {
  editorInstance = opts.editor;
  originalFormat = opts.format;
  documentType = opts.type;
  currentUserId = opts.userId;
  uploadCallback = opts.onUpload;
  saveLockBroadcast = opts.onSaveLock ?? null;
  lastCheckpointIndex = getPatchIndex();
  lastCheckpointTime = Date.now();

  // Start auto-save timer
  if (autoSaveTimer) clearInterval(autoSaveTimer);
  autoSaveTimer = setInterval(() => {
    checkAndSave();
  }, CHECKPOINT_TIME_INTERVAL_MS);
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

  if (shouldSave && !isSaving) {
    await saveCheckpoint();
  }
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
    return; // Another user is saving
  }

  isSaving = true;
  saveLockBroadcast?.(true);

  try {
    // Extract current document as binary from OnlyOffice
    // asc_nativeGetFile() returns the document in OnlyOffice's internal format
    const binData: Uint8Array = editorInstance.asc_nativeGetFile();

    if (!binData || binData.length === 0) {
      console.warn('Checkpoint: empty document, skipping save');
      return;
    }

    // Convert .bin → original format (e.g. docx, xlsx, pptx)
    const converted = await convertFromInternal(
      binData.buffer,
      originalFormat,
      documentType
    );

    // Upload (encryption happens in the callback)
    await uploadCallback(converted.buffer, originalFormat);

    lastCheckpointIndex = getPatchIndex();
    lastCheckpointTime = Date.now();
  } catch (error) {
    console.error('Checkpoint save failed:', error);
  } finally {
    isSaving = false;
    releaseSaveLock(currentUserId);
    saveLockBroadcast?.(false);
  }
}
