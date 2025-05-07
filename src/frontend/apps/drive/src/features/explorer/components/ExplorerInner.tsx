import { SelectionArea, SelectionEvent } from "@viselect/react";
import { ExplorerGrid } from "./grid/ExplorerGrid";
import {
  ExplorerBreadcrumbs,
  ExplorerBreadcrumbsMobile,
} from "./ExplorerBreadcrumbs";
import { useExplorer } from "./ExplorerContext";
import { ExplorerSelectionBar } from "./ExplorerSelectionBar";
import clsx from "clsx";
import { Item } from "@/features/drivers/types";
import { useEffect, useRef } from "react";
import { ExplorerProps } from "./Explorer";
import { useTranslation } from "react-i18next";
import { ExplorerFilters } from "./ExplorerFilters";
export type FileUploadMeta = { file: File; progress: number };

export const ExplorerInner = (props: ExplorerProps) => {
  const {
    setSelectedItems,
    itemId,
    setRightPanelForcedItem,
    displayMode,
    selectedItems,
    dropZone,
  } = useExplorer();

  const { t } = useTranslation();

  const ref = useRef<Item[]>([]);
  ref.current = selectedItems;

  const onSelectionStart = ({ event, selection }: SelectionEvent) => {
    if (!event?.ctrlKey && !event?.metaKey) {
      selection.clearSelection();
      setSelectedItems([]);
    }
    setRightPanelForcedItem(undefined);
  };

  const getChildItem = (id: string): Item => {
    const child = props.childrenItems?.find((childItem) => childItem.id === id);
    if (!child) {
      throw new Error("Cannot find child with id " + id);
    }
    return child;
  };

  const onSelectionMove = ({
    store: {
      changed: { added, removed },
    },
  }: SelectionEvent) => {
    setRightPanelForcedItem(undefined);
    setSelectedItems((prev) => {
      let next = [...prev];

      added.forEach((element) => {
        const id = element.getAttribute("data-id");
        if (id) {
          next.push(getChildItem(id)!);
        }
      });

      removed.forEach((element) => {
        const id = element.getAttribute("data-id");
        if (id) {
          next = next.filter((item) => item.id !== id);
        }
      });

      return next;
    });
  };

  // See below in <SelectionArea> for more details on why we need to use a ref here.
  const onSelectionMoveRef = useRef(onSelectionMove);
  onSelectionMoveRef.current = onSelectionMove;

  /**
   * We prevent the the range selection if the target is not a name or a title
   */
  const beforeDrag = (target: HTMLElement): boolean => {
    const isName = target.closest(".explorer__grid__item__name__text");
    const isTitle = target.closest(".explorer__tree__item__title");

    if (isName || isTitle) {
      return false;
    }

    const parent = target.closest(".selectable");
    if (parent) {
      const isSelected = parent.classList.contains("selected");
      return !isSelected;
    }

    return true;
  };

  /**
   * When a user clicks outside the folder zone we want to reset its selection
   */
  const onBeforeStart = ({ event, selection }: SelectionEvent) => {
    if (!event?.target) {
      return false;
    }

    const target = event.target as HTMLElement;
    if (!beforeDrag(target)) {
      return false;
    }

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

    if (hasAnyClass && !event?.ctrlKey && !event?.metaKey) {
      selection.clearSelection();
      setSelectedItems([]);
    }
  };

  // We clear the selection when the itemId changes
  useEffect(() => {
    if (itemId) {
      setSelectedItems([]);
    }
  }, [itemId]);

  return (
    <SelectionArea
      onBeforeStart={onBeforeStart}
      onStart={onSelectionStart}
      onMove={(params) => {
        // This pattern might seem weird, but SelectionArea memorizes the first passed params, even if the callbacks
        // are updated. In order to be able to query the most recent props, we need to use a ref.
        // Related to this: https://github.com/simonwep/viselect/blob/9d902cd32405d0a9a26f6adb8aacbf5c18b0a3f9/packages/react/src/SelectionArea.tsx#L23-L44
        onSelectionMoveRef.current(params);
      }}
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
      <ExplorerBreadcrumbsMobile />
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
            <ExplorerFilters />
          )}

          <div className="explorer__content">
            {props.gridHeader ? props.gridHeader : <ExplorerBreadcrumbs />}
            <ExplorerGrid {...props} />
          </div>
        </div>
      </div>
    </SelectionArea>
  );
};
