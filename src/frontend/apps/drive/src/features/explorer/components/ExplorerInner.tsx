import { SelectionArea, SelectionEvent } from "@viselect/react";
import { ExplorerGrid } from "./ExplorerGrid";
import { ExplorerBreadcrumbs } from "./ExplorerBreadcrumbs";
import { useExplorer } from "./ExplorerContext";
import { ExplorerSelectionBar } from "./ExplorerSelectionBar";
import { useDropzone } from "react-dropzone";
import clsx from "clsx";
import { useMutation } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { useEffect, useRef, useState } from "react";
import {
  addToast,
  Toaster,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useTranslation } from "react-i18next";
import { Id, toast } from "react-toastify";
import { FileUploadToast } from "./toasts/FileUploadToast";
export type FileUploadMeta = { file: File; progress: number };

export const ExplorerInner = () => {
  const { t } = useTranslation();
  const {
    setSelectedItemIds: setSelectedItems,
    item,
    displayMode,
    selectedItems,
  } = useExplorer();
  const driver = getDriver();

  const onSelectionStart = ({ event, selection }: SelectionEvent) => {
    if (!event?.ctrlKey && !event?.metaKey) {
      selection.clearSelection();
      setSelectedItems({});
    }
  };

  const onSelectionMove = ({
    store: {
      changed: { added, removed },
    },
  }: SelectionEvent) => {
    setSelectedItems((prev) => {
      const next = { ...prev };
      added.forEach((element) => {
        const id = element.getAttribute("data-id");
        if (id) next[id] = true;
      });
      removed.forEach((element) => {
        const id = element.getAttribute("data-id");
        if (id) delete next[id];
      });
      return next;
    });
  };

  const queryClient = useQueryClient();
  const createFile = useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.createFile>) => {
      await driver.createFile(...payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", item!.id],
      });
    },
  });

  const fileDragToastId = useRef<Id | null>(null);
  const fileUploadsToastId = useRef<Id | null>(null);
  const [uploadingState, setUploadingState] = useState<
    Record<string, FileUploadMeta>
  >({});

  // Debug
  // const [uploadingState, setUploadingState] = useState<
  //   Record<string, FileUploadMeta>
  // >({
  //   "image.png": { file: new File([], "image.png"), progress: 0 },
  //   "video.mp4": { file: new File([], "video.mp4"), progress: 0 },
  //   "audio.mp3": { file: new File([], "audio.mp3"), progress: 0 },
  //   "document.pdf": { file: new File([], "document.pdf"), progress: 0 },
  //   "image2.png": { file: new File([], "image2.png"), progress: 0 },
  //   "image3.png": { file: new File([], "image3.png"), progress: 0 },
  //   "image4.png": { file: new File([], "image4.png"), progress: 0 },
  //   "image5.png": { file: new File([], "image5.png"), progress: 0 },
  // });
  // useEffect(() => {
  //   if (fileUploadsToastId.current) {
  //     return;
  //   }
  //   fileUploadsToastId.current = addToast(
  //     <FileUploadToast uploadingState={uploadingState} />,
  //     {
  //       autoClose: false,
  //     }
  //   );
  //   const interval = setInterval(() => {
  //     setUploadingState((prev) => {
  //       return Object.fromEntries(
  //         Object.entries(prev).map(([key, meta]) => [
  //           key,
  //           {
  //             ...meta,
  //             progress: meta.progress + Math.floor(Math.random() * 21) + 10,
  //           },
  //         ])
  //       );
  //     });
  //   }, 1000);
  // }, []);

  useEffect(() => {
    if (fileUploadsToastId.current) {
      toast.update(fileUploadsToastId.current, {
        render: <FileUploadToast uploadingState={uploadingState} />,
      });
    }
  }, [uploadingState]);

  const { getRootProps, getInputProps, isFocused, isDragAccept, isDragReject } =
    useDropzone({
      noClick: true,
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
        for (const file of acceptedFiles) {
          setUploadingState((prev) => {
            const newState = {
              ...prev,
              [file.name]: { file, progress: 0 },
            };
            return newState;
          });
        }

        // Then, upload all the files sequentially. We are not uploading them in parallel because the backend
        // does not support it, it causes concurrency issues.
        for (const file of acceptedFiles) {
          await createFile.mutateAsync({
            filename: file.name,
            file,
            parentId: item!.id,
            progressHandler: (progress) => {
              setUploadingState((prev) => {
                const newState = {
                  ...prev,
                  [file.name]: { file, progress },
                };
                return newState;
              });
            },
          });
        }
      },
    });

  return (
    <SelectionArea
      onStart={onSelectionStart}
      onMove={onSelectionMove}
      selectables=".selectable"
      className="selection-area__container"
      features={{
        range: true,
        touch: true,
        singleTap: {
          // We do not want to allow singleTap to select items, otherwise it overrides the onClick event of the TR
          // element, and also blocks the click on the action dropdown menu. We rather implement it by ourselves.
          allow: false,
          intersect: "native",
        },
      }}
    >
      <div
        {...getRootProps({
          className: clsx(`explorer explorer--${displayMode}`, {
            "explorer--drop-zone--focused": isFocused,
            "explorer--drop-zone--drag-accept": isDragAccept,
            "explorer--drop-zone--drag-reject": isDragReject,
          }),
        })}
      >
        <input {...getInputProps()} />
        <div className="explorer__container">
          {selectedItems.length > 0 ? (
            <ExplorerSelectionBar />
          ) : (
            <div className="explorer__filters">Filters</div>
          )}

          <div className="explorer__content">
            <ExplorerBreadcrumbs />
            <ExplorerGrid />
          </div>
        </div>
        <Toaster />
      </div>
    </SelectionArea>
  );
};
