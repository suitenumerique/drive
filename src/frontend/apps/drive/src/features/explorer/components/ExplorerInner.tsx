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
import { Item } from "@/features/drivers/types";
export type FileUploadMeta = { file: File; progress: number };

export const ExplorerInner = () => {
  const { t } = useTranslation();
  const {
    setSelectedItemIds: setSelectedItems,
    itemId,
    item,
    displayMode,
    selectedItems,
  } = useExplorer();

  const ref = useRef<Item[]>([]);
  const driver = getDriver();
  ref.current = selectedItems;

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
      return driver.createFile(...payload);
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

  useEffect(() => {
    if (itemId) {
      setSelectedItems({});
    }
  }, [itemId]);

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
        const promises = [];
        for (const file of acceptedFiles) {
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
                  },
                  {
                    onError: () => {
                      setUploadingState((prev) => {
                        // Remove the file from the uploading state on error
                        const newState = { ...prev };
                        delete newState[file.name];
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

  const beforeDrag = (target: HTMLElement): boolean => {
    const isName = target.closest(".explorer__grid__item__name__text");

    if (isName) {
      console.log("isName");
      return false;
    }

    const parent = target.closest(".selectable");
    if (parent) {
      const isSelected = parent.classList.contains("selected");
      return !isSelected;
    }
    return true;
  };

  return (
    <SelectionArea
      onBeforeDrag={(ev) => {
        return beforeDrag(ev.event?.target as HTMLElement);
      }}
      onBeforeStart={({ event, selection }) => {
        if (!event?.target) {
          return;
        }
        const target = event.target as HTMLElement;

        const classesToCheck = [
          "explorer__content",
          "explorer--app",
          "c__breadcrumbs__button",
          "explorer__content__breadcrumbs",
          "explorer__content__filters",
        ];
        const hasAnyClass = classesToCheck.some((className) =>
          target.classList.contains(className)
        );
        if (hasAnyClass) {
          selection.clearSelection();
          setSelectedItems({});
        }
      }}
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
