import { SelectionArea, SelectionEvent } from "@viselect/react";

import clsx from "clsx";
import { Item } from "@/features/drivers/types";
import { useEffect, useRef } from "react";
import { useAppExplorer } from "./AppExplorer";
import { ContextMenu, useResponsive } from "@gouvfr-lasuite/ui-kit";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import { useSetSelectedItems } from "@/features/explorer/stores/selectionStore";
import { AppExplorerSelectionBarGate } from "./AppExplorerSelectionBarGate";
import {
  AppExplorerBreadcrumbs,
  ExplorerBreadcrumbsMobile,
} from "@/features/explorer/components/app-view/AppExplorerBreadcrumbs";
import { AppExplorerGrid } from "@/features/explorer/components/app-view/AppExplorerGrid";
import { useCreateMenuItems } from "../../hooks/useCreateMenuItems";


/**
 * - Handles the area selection of items
 * - Selection bar
 * - Filters
 */
export const AppExplorerInner = () => {
  const appExplorer = useAppExplorer();
  const {
    itemId,
    setRightPanelForcedItem,
    displayMode,
    dropZone,
  } = useGlobalExplorer();
  const setSelectedItems = useSetSelectedItems();
  const showFilters = appExplorer.showFilters ?? true;
  const onSelectionStart = ({ event, selection }: SelectionEvent) => {
    if (!event?.ctrlKey && !event?.metaKey) {
      selection.clearSelection();
      setSelectedItems([]);
    }
    setRightPanelForcedItem(undefined);
  };

  const getChildItem = (id: string): Item => {
    const child = appExplorer.childrenItems?.find(
      (childItem) => childItem.id === id,
    );
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

    if (added.length == 0 && removed.length == 0) {
      return;
    }

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
      target.classList.contains(className),
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

  const { isTablet } = useResponsive();

  const { menuItems: contextMenuItems, modals: createModals } =
    useCreateMenuItems({ includeImport: true });

  const renderContent = () => {
    return (
      <ContextMenu options={contextMenuItems}>
        {displayMode === "app" && <ExplorerBreadcrumbsMobile />}
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
            <AppExplorerSelectionBarGate showFilters={showFilters} />

            <div className="explorer__content">
              {appExplorer.gridHeader ? (
                appExplorer.gridHeader
              ) : (
                <AppExplorerBreadcrumbs />
              )}

              <div className="explorer__grid__container">
                <AppExplorerGrid />
              </div>
            </div>
          </div>
        </div>
      </ContextMenu>
    );
  };

  if (isTablet || appExplorer.disableAreaSelection) {
    return (
      <>
        {renderContent()}

        {createModals}
      </>
    );
  }

  return (
    <>
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
        {renderContent()}
      </SelectionArea>
      {createModals}
    </>
  );
};
