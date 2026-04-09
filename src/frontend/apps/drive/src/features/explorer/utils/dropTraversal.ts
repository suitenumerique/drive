import { fromEvent, FileWithPath } from "file-selector";

/**
 * Custom drop traversal that preserves empty folders.
 *
 * react-dropzone's default getFilesFromEvent (from `file-selector`) walks
 * dropped directories via webkitGetAsEntry() but silently drops empty
 * folders: when readEntries() returns an empty batch, no entry is produced
 * and the folder is lost.
 *
 * This module re-implements the drag traversal so that every empty
 * directory yields a marker File. The marker is a real (zero-byte) File
 * object — so it travels through the react-dropzone pipeline like any
 * other file — but it carries an `isEmptyFolder` flag and a path that
 * useUpload uses to materialize the folder hierarchy without ever
 * uploading the marker to the backend.
 *
 * Input change events (the "Import folder/files" buttons) are delegated
 * to file-selector's default behavior. The browser does not expose empty
 * folders through <input webkitdirectory>, so this is an accepted
 * limitation matching Google Drive / Proton Drive.
 */

export const EMPTY_FOLDER_MARKER_NAME = ".empty-folder";

const EMPTY_FOLDER_MARKER_TYPE = "application/x-empty-folder-marker";

export type EmptyFolderMarker = FileWithPath & { isEmptyFolder: true };

/**
 * Creates a zero-byte File object that marks the existence of an empty
 * directory at `dirPath`. The marker's path is `<dirPath>/.empty-folder`
 * so that useUpload's getFolderByPath splits it into the directory chain
 * and ignores the trailing marker name.
 *
 * @internal exported for unit tests
 */
export const createEmptyFolderMarker = (
  dirPath: string,
): EmptyFolderMarker => {
  const marker = new File([], EMPTY_FOLDER_MARKER_NAME, {
    type: EMPTY_FOLDER_MARKER_TYPE,
  }) as EmptyFolderMarker;
  Object.defineProperty(marker, "path", {
    value: `${dirPath}/${EMPTY_FOLDER_MARKER_NAME}`,
    writable: false,
    enumerable: true,
    configurable: true,
  });
  Object.defineProperty(marker, "isEmptyFolder", {
    value: true,
    writable: false,
    enumerable: true,
    configurable: true,
  });
  return marker;
};

/** Tells whether a File is an empty folder marker created by this module. */
export const isEmptyFolderMarker = (file: File): boolean => {
  return (file as EmptyFolderMarker).isEmptyFolder === true;
};

/**
 * Reads ALL entries from a FileSystemDirectoryReader. The native
 * readEntries() returns batches (~100 entries) and must be called in a
 * loop until it yields an empty batch. Older Safari versions had a bug
 * where they only returned the first batch — looping is required for
 * correctness.
 *
 * @internal exported for unit tests
 */
export const readAllEntries = (
  reader: FileSystemDirectoryReader,
): Promise<FileSystemEntry[]> => {
  return new Promise((resolve, reject) => {
    const all: FileSystemEntry[] = [];
    const readBatch = () => {
      reader.readEntries(
        (batch) => {
          if (batch.length === 0) {
            resolve(all);
            return;
          }
          all.push(...batch);
          readBatch();
        },
        (err) => reject(err),
      );
    };
    readBatch();
  });
};

/** @internal exported for unit tests */
export const getFileFromEntry = (
  entry: FileSystemFileEntry,
): Promise<FileWithPath> => {
  return new Promise((resolve, reject) => {
    entry.file(
      (file) => {
        const fwp = file as FileWithPath;
        Object.defineProperty(fwp, "path", {
          value: entry.fullPath,
          writable: false,
          enumerable: true,
          configurable: true,
        });
        resolve(fwp);
      },
      (err) => reject(err),
    );
  });
};

/**
 * Recursively walks a FileSystemEntry. Files are returned as FileWithPath,
 * non-empty directories yield their flattened contents, and empty
 * directories yield a single empty-folder marker.
 *
 * @internal exported for unit tests
 */
export const traverseEntry = async (
  entry: FileSystemEntry,
): Promise<(FileWithPath | EmptyFolderMarker)[]> => {
  if (entry.isFile) {
    const file = await getFileFromEntry(entry as FileSystemFileEntry);
    return [file];
  }

  if (entry.isDirectory) {
    const dirEntry = entry as FileSystemDirectoryEntry;
    const children = await readAllEntries(dirEntry.createReader());

    if (children.length === 0) {
      return [createEmptyFolderMarker(dirEntry.fullPath)];
    }

    const nested = await Promise.all(children.map(traverseEntry));
    return nested.flat();
  }

  return [];
};

const isDragEventWithItems = (
  evt: unknown,
): evt is { dataTransfer: DataTransfer } => {
  if (typeof evt !== "object" || evt === null) return false;
  const dt = (evt as { dataTransfer?: DataTransfer }).dataTransfer;
  return !!dt && !!dt.items;
};

/**
 * Drop-in replacement for react-dropzone's `getFilesFromEvent`.
 *
 * - DragEvent with dataTransfer.items: walks the entry tree ourselves
 *   so empty folders surface as markers. Falls back to file-selector's
 *   default if webkitGetAsEntry is unavailable on the items.
 * - Anything else (input change, FileSystemHandle array, etc.): delegated
 *   to file-selector's `fromEvent`.
 */
export const customGetFilesFromEvent = async (
  evt: unknown,
): Promise<(FileWithPath | EmptyFolderMarker | DataTransferItem)[]> => {
  if (!isDragEventWithItems(evt)) {
    return fromEvent(evt as Event);
  }

  const dt = evt.dataTransfer;
  const items = Array.from(dt.items).filter((item) => item.kind === "file");

  // Mirror file-selector: on non-drop events (dragenter/dragover) the
  // browser restricts access to item contents, so there is no point in
  // walking the entry tree. Return the raw DataTransferItem[]
  // synchronously — this is exactly what react-dropzone expects on those
  // events, and any deviation breaks its event hand-shake (including the
  // onDragEnter toast). The async webkitGetAsEntry() walk only runs on
  // the real 'drop' event.
  const evtType = (evt as unknown as { type?: string }).type;
  if (evtType !== "drop") {
    return items;
  }

  // If webkitGetAsEntry isn't available on the items, fall back to the
  // default behavior so we don't break drag & drop in unsupported
  // contexts.
  const supportsEntries = items.every(
    (item) => typeof item.webkitGetAsEntry === "function",
  );
  if (!supportsEntries) {
    return fromEvent(evt as unknown as Event);
  }

  // Snapshot every entry SYNCHRONOUSLY before any await. On a real
  // 'drop' event the DataTransferItem objects become inert after the
  // first microtask tick, so calling webkitGetAsEntry() on later items
  // after an await returns null — which silently drops every item past
  // the first. We therefore pull all entries up front, then walk them
  // asynchronously with Promise.all (mirroring what file-selector does
  // via `items.map(toFilePromises)`).
  const entries: FileSystemEntry[] = [];
  for (const item of items) {
    const entry = item.webkitGetAsEntry();
    if (entry) entries.push(entry);
  }

  const walked = await Promise.all(entries.map(traverseEntry));
  return walked.flat();
};
