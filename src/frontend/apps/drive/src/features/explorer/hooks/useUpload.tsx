import { useEffect } from "react";
import { toast } from "react-toastify";
import { Item } from "@/features/drivers/types";
import { FileWithPath, useDropzone } from "react-dropzone";
import { useMutationCreateFolder } from "./useMutations";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { useTranslation } from "react-i18next";
import { useRef } from "react";
import { Id } from "react-toastify";
import { FileUploadMeta } from "../components/ExplorerInner";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { FileUploadToast } from "../components/toasts/FileUploadToast";

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
    parentItem: Item,
    folderUploads: FolderUpload[]
  ) => {
    const promises = [];
    for (const folder of folderUploads) {
      promises.push(
        () =>
          new Promise<void>((resolve) => {
            createFolder.mutate(
              {
                title: folder.item.title!,
                parentId: parentItem.id,
              },
              {
                onSuccess: async (createdFolder) => {
                  folder.files.forEach((file) => {
                    file.parentId = createdFolder.id;
                  });
                  await createFoldersFromDrop(createdFolder, folder.children);
                  resolve();
                },
              }
            );
          })
      );
    }
    for (const promise of promises) {
      await promise();
    }
  };

  // Assign each file a parentId and create the folders if it is a folder upload.
  const handleHierarchy = async (upload: Upload) => {
    upload.folder.files.forEach((file) => {
      file.parentId = item!.id;
    });
    await createFoldersFromDrop(item!, upload.folder.children);
  };

  return {
    handleHierarchy,
    filesToUpload,
  };
};

/**
 * This function removes the leading "./" or "/" from the path.
 */
const pathNicefy = (path: string) => {
  return path.replace(/^[./]+/, "");
};

export const useUploadZone = ({ item }: { item: Item }) => {
  const driver = getDriver();

  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const createFile = useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.createFile>) => {
      return driver.createFile(...payload);
    },
    onSuccess: (data, variables) => {
      if (variables.parentId) {
        queryClient.invalidateQueries({
          queryKey: ["items", variables.parentId],
        });
      }
    },
  });

  const fileDragToastId = useRef<Id | null>(null);
  const fileUploadsToastId = useRef<Id | null>(null);
  const [uploadingState, setUploadingState] = useState<
    Record<string, FileUploadMeta>
  >({});

  const { filesToUpload, handleHierarchy } = useUpload({ item: item! });

  const dropZone = useDropzone({
    noClick: true,
    useFsAccessApi: false,
    // If we do not set this, the click on the "..." menu of each items does not work, also click + select on items
    // does not work too. It might seems related to onFocus and onBlur events.
    noKeyboard: true,
    onDragEnter: () => {
      if (fileDragToastId.current) {
        return;
      }
      fileDragToastId.current = addToast(
        <ToasterItem>
          <span className="material-icons">cloud_upload</span>
          <span>
            {t("explorer.actions.upload.toast", { title: item?.title })}
          </span>
        </ToasterItem>,
        { autoClose: false }
      );
    },
    onDragLeave: () => {
      if (fileDragToastId.current) {
        toast.dismiss(fileDragToastId.current);
        fileDragToastId.current = null;
      }
    },
    onDrop: async (acceptedFiles) => {
      const upload = filesToUpload(acceptedFiles);
      await handleHierarchy(upload);

      if (fileDragToastId.current) {
        toast.dismiss(fileDragToastId.current);
        fileDragToastId.current = null;
      }

      if (!fileUploadsToastId.current) {
        fileUploadsToastId.current = addToast(
          <FileUploadToast uploadingState={uploadingState} />,
          {
            autoClose: false,
            onClose: () => {
              // We need to set this to null in order to re-show the toast when the user drops another file later.
              fileUploadsToastId.current = null;
            },
          }
        );
      }

      // Do not run "setUploadingState({});" because if a uploading is still in progress, it will be overwritten.

      // First, add all the files to the uploading state in order to display them in the toast.
      for (const file of upload.files) {
        setUploadingState((prev) => {
          const newState = {
            ...prev,
            [pathNicefy(file.path!)]: { file, progress: 0 },
          };
          return newState;
        });
      }

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
                  parentId: file.parentId!,
                  progressHandler: (progress) => {
                    setUploadingState((prev) => {
                      const newState = {
                        ...prev,
                        [pathNicefy(file.path!)]: { file, progress },
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
                      delete newState[pathNicefy(file.path!)];
                      return newState;
                    });
                  },
                  onSettled: () => {
                    resolve();
                  },
                }
              );
            })
        );
      }
      for (const promise of promises) {
        await promise();
      }
    },
  });

  useEffect(() => {
    if (fileUploadsToastId.current) {
      if (Object.keys(uploadingState).length === 0) {
        toast.dismiss(fileUploadsToastId.current);
        fileUploadsToastId.current = null;
      } else {
        toast.update(fileUploadsToastId.current, {
          render: <FileUploadToast uploadingState={uploadingState} />,
        });
      }
    }
  }, [uploadingState]);

  return {
    dropZone,
  };
};
