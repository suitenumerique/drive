import { SelectionArea, SelectionEvent } from "@viselect/react";
import { ExplorerGrid } from "./ExplorerGrid";
import { ExplorerBreadcrumbs } from "./ExplorerBreadcrumbs";
import { useExplorer } from "./ExplorerContext";
import { ExplorerSelectionBar } from "./ExplorerSelectionBar";
import clsx from "clsx";
import { useTranslation } from "react-i18next";
export type FileUploadMeta = { file: File; progress: number };

export const ExplorerInner = () => {
  const { t } = useTranslation();
  const {
    setSelectedItemIds: setSelectedItems,
    displayMode,
    selectedItems,
    dropZone,
  } = useExplorer();

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
        {...dropZone.getRootProps({
          className: clsx(`explorer explorer--${displayMode}`, {
            "explorer--drop-zone--focused": dropZone.isFocused,
            "explorer--drop-zone--drag-accept": dropZone.isDragAccept,
            "explorer--drop-zone--drag-reject": dropZone.isDragReject,
          }),
        })}
      >
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
      </div>
    </SelectionArea>
  );
};
