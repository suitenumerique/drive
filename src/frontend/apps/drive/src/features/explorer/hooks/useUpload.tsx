import { useCallback, useEffect } from "react";
import { toast } from "react-toastify";
import { Item } from "@/features/drivers/types";
import { FileWithPath, useDropzone } from "react-dropzone";
import { useMutationCreateFolder } from "./useMutations";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useRef } from "react";
import { Id } from "react-toastify";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { FileUploadToast } from "../components/toasts/FileUploadToast";
import { useQueryClient } from "@tanstack/react-query";
import { getEntitlements } from "@/utils/entitlements";
import { useCanCreateChildren } from "@/features/items/utils";
import { getMyFilesQueryKey } from "@/utils/defaultRoutes";
import { useConfig } from "@/features/config/ConfigProvider";
import { getDriver } from "@/features/config/Config";
import { APIError } from "@/features/api/APIError";
import { useRefreshQueryCacheAfterMutation } from "./useRefreshItems";
import { isIdInItemTree } from "../utils/utils";

type ActiveUpload = {
  file: FileUpload;
  // Materialized path of the drop target folder (e.g. "root.A.B").
  // Used by cancelUploadsForDeletedItems to detect ancestor deletions.
  parentPath: string;
  // Populated once the upload actually starts. Undefined while still queued.
  abort?: () => Promise<void>;
};
import { formatSize } from "@/features/explorer/utils/utils";
import {
  customGetFilesFromEvent,
  isEmptyFolderMarker,
} from "@/features/explorer/utils/dropTraversal";

type FileUpload = FileWithPath & {
  parentId?: string;
};

type FolderUpload = {
  item: Partial<Item>;
  files: FileUpload[];
  children: FolderUpload[];
  isCurrent?: boolean;
};

type Upload = {
  // The current folder.
  folder: FolderUpload;
  type: "folder" | "file";
  files: FileUpload[];
};

const useUpload = ({ item }: { item: Item }) => {
  const createFolder = useMutationCreateFolder();
  const queryClient = useQueryClient();

  /**
   * TODO: Test.
   *
   * This function is used to convert the files to upload into an Upload object.
   */
  const filesToUpload = (files: FileWithPath[]): Upload => {
    const folder = {
      item: item,
      files: [],
      children: [],
      isCurrent: true,
    };

    const findFolder = (folders: FolderUpload[], name: string) => {
      for (const folder of folders) {
        if (folder.item!.title === name) {
          return folder;
        }
      }
      return null;
    };

    const getFolder = (folders: FolderUpload[], name: string): FolderUpload => {
      const folder = findFolder(folders, name);
      if (folder) {
        return folder;
      }
      const newFolder = {
        item: {
          title: name,
        },
        files: [],
        children: [],
      };
      folders.push(newFolder);
      return newFolder;
    };

    /**
     * path can be like:
     * - /path/to/file.txt
     * - path/to/file.txt
     * - ./path/to/file.txt
     */
    const getFolderByPath = (path: string) => {
      // remove last part, last is the file name.
      const parts = path.split("/").slice(0, -1);

      // Remove empty first element if it exists, it is made to handle /path/to/file.txt type of path.
      // split gives ["", "path", "to", "file.txt"] we want ["path", "to"].
      // Remove "." if it exists, it is made to handle ./path/to/file.txt type of path.
      // split gives [".", "path", "to", "file.txt"] we want ["path", "to"].
      if (parts.length > 0 && (parts[0] === "" || parts[0] === ".")) {
        parts.shift();
      }

      // If there is no more parts, return the current folder.
      if (parts.length === 0) {
        return folder;
      }

      let current = getFolder(folder.children, parts[0]);
      for (let i = 1; i < parts.length; i++) {
        current = getFolder(current.children, parts[i]);
      }
      return current;
    };

    for (const file of files) {
      const folder = getFolderByPath(file.path!);
      // Empty-folder markers exist solely to materialize the folder chain
      // via getFolderByPath above. They must never end up in folder.files,
      // otherwise the upload loop would try to send them to the backend.
      if (isEmptyFolderMarker(file)) {
        continue;
      }
      folder.files.push(file);
    }
    return {
      folder,
      type: "folder",
      files,
    };
  };

  // Create the folders and assign each file a parentId.
  const createFoldersFromDrop = async (
    parentItem: Item | undefined,
    folderUploads: FolderUpload[],
  ) => {
    const promises = [];

    for (const folder of folderUploads) {
      promises.push(
        () =>
          new Promise<void>((resolve) => {
            createFolder.mutate(
              {
                title: folder.item.title!,
                parentId: parentItem?.id,
              },
              {
                onSuccess: async (createdFolder) => {
                  queryClient.invalidateQueries({
                    queryKey: getMyFilesQueryKey(),
                  });

                  if (parentItem) {
                    queryClient.invalidateQueries({
                      queryKey: ["items", parentItem.id],
                    });
                  }

                  folder.files.forEach((file) => {
                    file.parentId = createdFolder.id;
                  });
                  await createFoldersFromDrop(createdFolder, folder.children);
                  resolve();
                },
              },
            );
          }),
      );
    }
    for (const promise of promises) {
      await promise();
    }
  };

  // Assign each file a parentId and create the folders if it is a folder upload.
  const handleHierarchy = async (upload: Upload) => {
    upload.folder.files.forEach((file) => {
      file.parentId = item?.id;
    });
    await createFoldersFromDrop(item, upload.folder.children);
  };

  return {
    handleHierarchy,
    filesToUpload,
  };
};

export enum FileUploadStatus {
  UPLOADING = "uploading",
  DONE = "done",
  ERROR = "error",
  CANCELLED = "cancelled",
}

export type FileUploadMeta = {
  file: File;
  progress: number;
  status: FileUploadStatus;
  error?: string;
};

export enum UploadingStep {
  NONE = "none",
  PREPARING = "preparing",
  CREATE_FOLDERS = "create_folders",
  UPLOAD_FILES = "upload_files",
  DONE = "done",
}

export type UploadingState = {
  step: UploadingStep;
  filesMeta: Record<string, FileUploadMeta>;
};

/**
 * This function removes the leading "./" or "/" from the path.
 */
const pathNicefy = (path: string) => {
  return path.replace(/^[./]+/, "");
};

export const useUploadZone = ({ item }: { item: Item }) => {
  const { t } = useTranslation();
  const { config } = useConfig();

  const driver = getDriver();
  const refresh = useRefreshQueryCacheAfterMutation();

  const canCreateChildren = useCanCreateChildren(item);

  const fileDragToastId = useRef<Id | null>(null);
  const fileUploadsToastId = useRef<Id | null>(null);
  const [uploadingState, setUploadingState] = useState<UploadingState>({
    step: UploadingStep.NONE,
    filesMeta: {},
  });

  // Single source of truth for queued + in-flight uploads. Map preserves
  // insertion order, giving us FIFO for free. An entry whose `abort` is
  // undefined is still queued; once upload starts we populate `abort`.
  // Removing an entry (delete/clear) is the cancellation signal.
  const activeUploadsRef = useRef<Map<string, ActiveUpload>>(new Map());
  // Whether the upload processing loop is currently running
  const isProcessingRef = useRef(false);

  const { filesToUpload, handleHierarchy } = useUpload({ item: item! });

  const onCancelFile = useCallback(async (fileName: string) => {
    const upload = activeUploadsRef.current.get(fileName);
    // Remove from the map first: this is the signal the processing loop
    // uses in its catch block to distinguish user cancel from real errors.
    activeUploadsRef.current.delete(fileName);
    if (upload?.abort) {
      await upload.abort();
    }
    setUploadingState((prev) => {
      const meta = prev.filesMeta[fileName];
      if (!meta || meta.status === FileUploadStatus.DONE) return prev;
      return {
        ...prev,
        filesMeta: {
          ...prev.filesMeta,
          [fileName]: {
            ...meta,
            status: FileUploadStatus.CANCELLED,
            progress: meta.progress,
          },
        },
      };
    });
  }, []);

  const onCancelAll = useCallback(async () => {
    // Snapshot entries before clearing so we can abort in-flight uploads.
    const entries = Array.from(activeUploadsRef.current.entries());
    activeUploadsRef.current.clear();
    for (const [, upload] of entries) {
      if (upload.abort) {
        await upload.abort();
      }
    }
    setUploadingState((prev) => {
      const newMeta = { ...prev.filesMeta };
      for (const [name] of entries) {
        const meta = newMeta[name];
        if (meta && meta.status === FileUploadStatus.UPLOADING) {
          newMeta[name] = { ...meta, status: FileUploadStatus.CANCELLED };
        }
      }
      return { ...prev, filesMeta: newMeta };
    });
  }, []);

  const validateDrop = () => {
    const canUpload = canCreateChildren;
    if (!canUpload) {
      return {
        code: "no-upload-rights",
        message: t("explorer.actions.upload.toast_no_rights"),
      };
    }
    return null;
  };

  const dismissDragToast = () => {
    if (!fileDragToastId.current) {
      return;
    }
    toast.dismiss(fileDragToastId.current);
    fileDragToastId.current = null;
  };

  const dropZone = useDropzone({
    noClick: true,
    useFsAccessApi: false,
    validator: validateDrop,
    // Custom traversal that preserves empty folders on drag & drop.
    // Input change events (folder/file buttons) are delegated to
    // file-selector inside this helper.
    getFilesFromEvent: customGetFilesFromEvent,
    // If we do not set this, the click on the "..." menu of each items does not work, also click + select on items
    // does not work too. It might seems related to onFocus and onBlur events.
    noKeyboard: true,
    onDragEnter: () => {
      if (fileDragToastId.current) {
        return;
      }

      const canUpload = canCreateChildren;

      fileDragToastId.current = addToast(
        <ToasterItem
          type={canUpload ? "info" : "error"}
          onDrop={dismissDragToast}
        >
          <span className="material-icons">cloud_upload</span>
          <span>
            {t(
              `explorer.actions.upload.toast${canUpload ? "" : "_no_rights"}`,
              {
                title: item?.title,
              },
            )}
          </span>
        </ToasterItem>,
        { autoClose: false },
      );
    },
    onDragLeave: (event) => {
      // Check if we're leaving the dropzone for a toast or staying within the dropzone area
      const relatedTarget = event.relatedTarget as Element;
      const isToastElement = relatedTarget?.closest(".Toastify");

      /*  If we're leaving the dropzone for a toast, we don't need to dismiss the toast.
       *  This is useful to avoid the flicker effect when the user drops a file over the toast.
       *  However, if we drop over a toast, the toast is never closed. This is because we added the onDrop={handleDrop} on the ToasterItem.
       */
      if (isToastElement) {
        return;
      }

      dismissDragToast();
    },
    onDrop: async (acceptedFiles) => {
      if (!canCreateChildren) {
        dismissDragToast();
        return;
      }

      // When the drop contains only empty-folder markers, there are no
      // real files to upload. In that case we skip the FileUploadToast
      // entirely and show a success toast once the folders have been created.
      const hasOnlyEmptyFolders =
        acceptedFiles.length > 0 &&
        acceptedFiles.every((file) => isEmptyFolderMarker(file));

      const showFileUploadToast = () => {
        if (hasOnlyEmptyFolders || fileUploadsToastId.current) {
          return;
        }
        fileUploadsToastId.current = addToast(
          <FileUploadToast
            uploadingState={uploadingState}
            onCancelFile={onCancelFile}
            onCancelAll={onCancelAll}
          />,
          {
            autoClose: false,
            onClose: () => {
              fileUploadsToastId.current = null;
            },
          },
        );
      };

      setUploadingState((prev) => ({
        ...prev,
        step: UploadingStep.PREPARING,
      }));

      showFileUploadToast();

      const entitlements = await getEntitlements();
      if (!entitlements.can_upload.result) {
        dismissDragToast();
        setUploadingState((prev) => ({
          ...prev,
          step: UploadingStep.NONE,
        }));
        addToast(
          <ToasterItem type="error">
            <span>
              {entitlements.can_upload.message ||
                t("entitlements.can_upload.cannot_upload")}
            </span>
          </ToasterItem>,
        );
        return;
      }

      setUploadingState((prev) => ({
        ...prev,
        step: UploadingStep.CREATE_FOLDERS,
      }));

      showFileUploadToast();
      dismissDragToast();

      const upload = filesToUpload(acceptedFiles);
      await handleHierarchy(upload);

      if (hasOnlyEmptyFolders) {
        setUploadingState((prev) => ({
          ...prev,
          step: UploadingStep.DONE,
        }));
        addToast(
          <ToasterItem type="info">
            <span>{t("explorer.actions.upload.folders_created")}</span>
          </ToasterItem>,
        );
        return;
      }

      // Strip empty-folder markers before any size/upload processing:
      // they are zero-byte sentinels whose only purpose was to make
      // filesToUpload create the corresponding FolderUpload nodes.
      const realFiles = upload.files.filter(
        (file) => !isEmptyFolderMarker(file),
      );

      // Filter out files that exceed the maximum upload size.
      const maxSize = config.DATA_UPLOAD_MAX_MEMORY_SIZE;
      const validFiles =
        maxSize !== undefined && maxSize !== null
          ? realFiles.filter((file) => file.size <= maxSize)
          : realFiles;
      const tooLargeFiles =
        maxSize !== undefined && maxSize !== null
          ? realFiles.filter((file) => file.size > maxSize)
          : [];
      if (maxSize !== undefined && maxSize !== null) {
        for (const file of tooLargeFiles) {
          addToast(
            <ToasterItem type="error">
              <span>
                {t("explorer.actions.upload.file_too_large", {
                  name: file.name,
                  maxSize: formatSize(maxSize, t),
                })}
              </span>
            </ToasterItem>,
          );
        }
      }

      // Do not run "setUploadingState({});" because if a uploading is still in progress, it will be overwritten.

      // First, add all the files to the uploading state in order to display them in the toast.
      const newFilesMeta: Record<string, FileUploadMeta> = {};
      for (const file of validFiles) {
        newFilesMeta[pathNicefy(file.path!)] = {
          file,
          progress: 0,
          status: FileUploadStatus.UPLOADING,
        };
      }
      for (const file of tooLargeFiles) {
        newFilesMeta[pathNicefy(file.path!)] = {
          file,
          progress: 0,
          status: FileUploadStatus.ERROR,
          error: "file_too_large",
        };
      }

      // Update UI state
      if (!isProcessingRef.current) {
        setUploadingState({
          step: UploadingStep.UPLOAD_FILES,
          filesMeta: newFilesMeta,
        });
      } else {
        setUploadingState((prev) => ({
          step: UploadingStep.UPLOAD_FILES,
          filesMeta: { ...prev.filesMeta, ...newFilesMeta },
        }));
      }

      // Enqueue valid files in the single source of truth. The materialized
      // path of the drop target is stored once per file so we can later
      // resolve "was an ancestor of this upload deleted?" via isIdInItemTree.
      const parentPath = item?.path ?? "";
      for (const file of validFiles) {
        activeUploadsRef.current.set(pathNicefy(file.path!), {
          file,
          parentPath,
        });
      }

      // If the processing loop is already running, it will pick up the new files
      if (isProcessingRef.current) {
        return;
      }

      // Start the processing loop
      isProcessingRef.current = true;

      // Pick the next queued entry: the first one without an abort handle
      // (abort === undefined means it hasn't started uploading yet).
      // Map iteration follows insertion order → FIFO is preserved.
      // The loop exits when no more queued entries remain.
      while (true) {
        let nextEntry: [string, ActiveUpload] | undefined;
        for (const entry of activeUploadsRef.current) {
          if (!entry[1].abort) {
            nextEntry = entry;
            break;
          }
        }
        if (!nextEntry) break;

        const [filePath, upload] = nextEntry;
        const file = upload.file;

        const { promise, abort } = driver.createFile({
          filename: file.name,
          file,
          parentId: file.parentId,
          progressHandler: (progress) => {
            setUploadingState((prev) => ({
              ...prev,
              filesMeta: {
                ...prev.filesMeta,
                [filePath]: {
                  file,
                  progress,
                  status:
                    progress >= 100
                      ? FileUploadStatus.DONE
                      : FileUploadStatus.UPLOADING,
                },
              },
            }));
          },
        });

        // Mark this entry as "in flight" so the loop won't pick it again.
        upload.abort = abort;

        try {
          await promise;
          // If the upload was cancelled mid-flight, the entry was removed
          // from the map: skip the success state update.
          if (!activeUploadsRef.current.has(filePath)) {
            continue;
          }
          activeUploadsRef.current.delete(filePath);
          refresh(file.parentId);
          setUploadingState((prev) => ({
            ...prev,
            filesMeta: {
              ...prev.filesMeta,
              [filePath]: {
                file,
                progress: 100,
                status: FileUploadStatus.DONE,
              },
            },
          }));
        } catch (err) {
          // If the entry was already removed from the map, onCancelFile (or
          // onCancelAll) ran while the upload was in flight → user cancel.
          const wasCancelled = !activeUploadsRef.current.has(filePath);
          activeUploadsRef.current.delete(filePath);
          if (
            wasCancelled ||
            (err instanceof DOMException && err.name === "AbortError")
          ) {
            // Already handled by onCancelFile/onCancelAll
            continue;
          }
          let errorCode = "unknown";
          if (err instanceof APIError && err.data?.errors?.[0]?.code) {
            errorCode = err.data.errors[0].code;
          }

          // Keep file in state with error status
          setUploadingState((prev) => ({
            ...prev,
            filesMeta: {
              ...prev.filesMeta,
              [filePath]: {
                file,
                progress: prev.filesMeta[filePath]?.progress ?? 0,
                status: FileUploadStatus.ERROR,
                error: errorCode,
              },
            },
          }));
        }
      }

      isProcessingRef.current = false;

      setUploadingState((prev) => ({
        ...prev,
        step: UploadingStep.DONE,
      }));
    },
  });

  useEffect(() => {
    if (fileUploadsToastId.current) {
      const activeFiles = Object.values(uploadingState.filesMeta).filter(
        (meta) => meta.status !== FileUploadStatus.CANCELLED,
      );
      // Dismiss toast if no active files remain during upload
      if (
        (uploadingState.step === UploadingStep.UPLOAD_FILES &&
          activeFiles.length === 0) ||
        uploadingState.step === UploadingStep.NONE
      ) {
        toast.dismiss(fileUploadsToastId.current);
        fileUploadsToastId.current = null;
      } else {
        toast.update(fileUploadsToastId.current, {
          render: (
            <FileUploadToast
              uploadingState={uploadingState}
              onCancelFile={onCancelFile}
              onCancelAll={onCancelAll}
            />
          ),
        });
      }
    }
  }, [uploadingState]);

  useEffect(() => {
    const unloadCallback = (event: BeforeUnloadEvent) => {
      if (
        [UploadingStep.CREATE_FOLDERS, UploadingStep.UPLOAD_FILES].includes(
          uploadingState.step,
        )
      ) {
        event.preventDefault();
      }
      return "";
    };

    window.addEventListener("beforeunload", unloadCallback);
    return () => window.removeEventListener("beforeunload", unloadCallback);
  }, [uploadingState.step]);

  /**
   * Cancel every active upload whose drop-target folder is — or is a
   * descendant of — any of the deleted items. We use isIdInItemTree to
   * check whether a deletedId appears anywhere in the materialized path,
   * which covers both direct parent and ancestor deletions.
   */
  const cancelUploadsForDeletedItems = useCallback(
    (deletedIds: string[]) => {
      if (activeUploadsRef.current.size === 0 || deletedIds.length === 0) {
        return;
      }
      // Collect matches first: onCancelFile mutates the map we're iterating.
      const toCancel: string[] = [];
      for (const [filePath, upload] of activeUploadsRef.current) {
        if (
          deletedIds.some((id) => isIdInItemTree(upload.parentPath, id))
        ) {
          toCancel.push(filePath);
        }
      }
      toCancel.forEach((filePath) => void onCancelFile(filePath));
    },
    [onCancelFile],
  );

  return {
    dropZone,
    cancelUploadsForDeletedItems,
  };
};
