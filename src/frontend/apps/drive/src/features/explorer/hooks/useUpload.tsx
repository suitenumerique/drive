import { useEffect } from "react";
import { toast } from "react-toastify";
import { Item } from "@/features/drivers/types";
import { FileWithPath, useDropzone } from "react-dropzone";
import { useMutationCreateFolder, useMutationCreateFile } from "./useMutations";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useRef } from "react";
import { Id } from "react-toastify";
import { FileUploadMeta } from "@/features/explorer/components/app-view/AppExplorerInner";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { FileUploadToast } from "../components/toasts/FileUploadToast";
import { useQueryClient } from "@tanstack/react-query";
import { getEntitlements } from "@/utils/entitlements";
import { useCanCreateChildren } from "@/features/items/utils";
import { getMyFilesQueryKey } from "@/utils/defaultRoutes";

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

enum UploadingStep {
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

  const createFile = useMutationCreateFile();

  const canCreateChildren = useCanCreateChildren(item);

  const fileDragToastId = useRef<Id | null>(null);
  const fileUploadsToastId = useRef<Id | null>(null);
  const [uploadingState, setUploadingState] = useState<UploadingState>({
    step: UploadingStep.NONE,
    filesMeta: {},
  });

  const { filesToUpload, handleHierarchy } = useUpload({ item: item! });

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

      setUploadingState((prev) => ({
        ...prev,
        step: UploadingStep.PREPARING,
      }));

      if (!fileUploadsToastId.current) {
        fileUploadsToastId.current = addToast(
          <FileUploadToast uploadingState={uploadingState} />,
          {
            autoClose: false,
            onClose: () => {
              // We need to set this to null in order to re-show the toast when the user drops another file later.
              fileUploadsToastId.current = null;
            },
          },
        );
      }

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

      if (!fileUploadsToastId.current) {
        fileUploadsToastId.current = addToast(
          <FileUploadToast uploadingState={uploadingState} />,
          {
            autoClose: false,
            onClose: () => {
              // We need to set this to null in order to re-show the toast when the user drops another file later.
              fileUploadsToastId.current = null;
            },
          },
        );
      }
      dismissDragToast();

      const upload = filesToUpload(acceptedFiles);
      await handleHierarchy(upload);

      // Do not run "setUploadingState({});" because if a uploading is still in progress, it will be overwritten.

      // First, add all the files to the uploading state in order to display them in the toast.
      const newUploadingState: UploadingState = {
        step: UploadingStep.UPLOAD_FILES,
        filesMeta: {},
      };
      for (const file of upload.files) {
        newUploadingState.filesMeta[pathNicefy(file.path!)] = {
          file,
          progress: 0,
        };
      }
      setUploadingState(newUploadingState);

      // Then, upload all the files sequentially. We are not uploading them in parallel because the backend
      // does not support it, it causes concurrency issues.
      const promises = [];
      for (const file of upload.files) {
        // We do not using "createFile.mutateAsync" because it causes unhandled errors.
        // Instead, we use a promise that we can await to run all the uploads sequentially.
        // Using "createFile.mutate" makes the error handled by the mutation hook itself.
        promises.push(
          () =>
            new Promise<void>((resolve) => {
              createFile.mutate(
                {
                  filename: file.name,
                  file,
                  parentId: file.parentId,
                  progressHandler: (progress) => {
                    setUploadingState((prev) => {
                      const newState = {
                        ...prev,
                        filesMeta: {
                          ...prev.filesMeta,
                          [pathNicefy(file.path!)]: { file, progress },
                        },
                      };
                      return newState;
                    });
                  },
                },
                {
                  onError: () => {
                    setUploadingState((prev) => {
                      // Remove the file from the uploading state on error
                      const newState = { ...prev };
                      delete newState.filesMeta[pathNicefy(file.path!)];
                      return newState;
                    });
                  },
                  onSettled: () => {
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
      setUploadingState((prev) => ({
        ...prev,
        step: UploadingStep.DONE,
      }));
    },
  });

  useEffect(() => {
    if (fileUploadsToastId.current) {
      // If the uploading state is "upload_files" and there are no files, we dismiss the toast.
      // It can happen if the upload fails for unknown reasons.
      if (
        (uploadingState.step === UploadingStep.UPLOAD_FILES &&
          Object.keys(uploadingState.filesMeta).length === 0) ||
        uploadingState.step === UploadingStep.NONE
      ) {
        toast.dismiss(fileUploadsToastId.current);
        fileUploadsToastId.current = null;
      } else {
        toast.update(fileUploadsToastId.current, {
          render: <FileUploadToast uploadingState={uploadingState} />,
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

  return {
    dropZone,
  };
};
