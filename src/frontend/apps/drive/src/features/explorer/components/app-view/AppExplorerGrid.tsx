import { Item } from "@/features/drivers/types";
import { useTranslation } from "react-i18next";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import clsx from "clsx";
import { Loader, useCunningham } from "@openfun/cunningham-react";
import gridEmpty from "@/assets/grid_empty.svg";
import {
  AppExplorerProps,
  useAppExplorer,
} from "@/features/explorer/components/app-view/AppExplorer";
import { EmbeddedExplorerGrid } from "../embedded-explorer/EmbeddedExplorerGrid";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { InfiniteScroll } from "@/features/ui/components/infinite-scroll/InfiniteScroll";

/**
 * Wrapper around EmbeddedExplorerGrid to display a list of items in a table.
 *
 * It provides:
 * - Runtime tree lazy loading support
 *
 * TODO: Refactor using EmbeddedExplorer
 *
 */
export const AppExplorerGrid = (props: AppExplorerProps) => {
  const { t } = useTranslation();
  const { t: tc } = useCunningham();

  const {
    setSelectedItems,
    selectedItems,
    onNavigate,
    setRightPanelForcedItem,
    item,
    displayMode,
    setPreviewItem,
    setPreviewItems,
  } = useGlobalExplorer();

  const { disableItemDragAndDrop } = useAppExplorer();
  const effectiveOnNavigate = props.onNavigate ?? onNavigate;

  const handleFileClick = (item: Item) => {
    if (item.url) {
      // We need to ensure the preview items list is updated when clicking on a file from the grid. Because this list
      // can be updated when clicking on a file from the search modal which sets the preview items to a list of one item.
      setPreviewItems(props.childrenItems ?? []);
      setPreviewItem(item);
    } else {
      addToast(<ToasterItem>{t("explorer.grid.no_url")}</ToasterItem>);
    }
  };

  const isLoading = props.isLoading || props.childrenItems === undefined;
  const isEmpty = props.childrenItems?.length === 0;
  const canCreateChildren = item?.abilities?.children_create;

  const getContent = () => {
    if (isLoading) {
      return <Loader aria-label={tc("components.datagrid.loader_aria")} />;
    }
    if (isEmpty) {
      // Use custom empty placeholder if provided
      if (props.emptyPlaceholder) {
        return props.emptyPlaceholder;
      }
      return (
        <div className="c__datagrid__empty-placeholder fs-h3 clr-greyscale-900 fw-bold">
          <img
            src={gridEmpty.src}
            alt={t("components.datagrid.empty_alt")}
            className="explorer__grid__empty__image"
          />
          <div className="explorer__grid__empty">
            <div className="explorer__grid__empty__caption">
              {canCreateChildren
                ? t("explorer.grid.empty.caption")
                : t("explorer.grid.empty.caption_no_create")}
            </div>
            <div className="explorer__grid__empty__cta">
              {canCreateChildren
                ? t("explorer.grid.empty.cta")
                : t("explorer.grid.empty.cta_no_create")}
            </div>
          </div>
        </div>
      );
    }

    const gridContent = (
      <EmbeddedExplorerGrid
        items={props.childrenItems}
        parentItem={item}
        gridActionsCell={props.gridActionsCell}
        onNavigate={effectiveOnNavigate}
        setRightPanelForcedItem={setRightPanelForcedItem}
        disableItemDragAndDrop={disableItemDragAndDrop}
        selectedItems={selectedItems}
        setSelectedItems={setSelectedItems}
        enableMetaKeySelection={true}
        displayMode={displayMode}
        canSelect={props.canSelect}
        onFileClick={handleFileClick}
      />
    );

    // If infinite scroll props are provided, wrap with InfiniteScroll
    if (props.hasNextPage !== undefined && props.fetchNextPage) {
      return (
        <InfiniteScroll
          hasNextPage={props.hasNextPage}
          isFetchingNextPage={props.isFetchingNextPage || false}
          fetchNextPage={props.fetchNextPage}
        >
          {gridContent}
        </InfiniteScroll>
      );
    }

    return gridContent;
  };

  return (
    <div
      className={clsx("c__datagrid explorer__grid", {
        "c__datagrid--empty": isEmpty,
        "c__datagrid--loading": isLoading,
      })}
    >
      {getContent()}
    </div>
  );
};
