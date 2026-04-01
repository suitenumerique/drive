import { Item } from "@/features/drivers/types";
import { useTranslation } from "react-i18next";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import clsx from "clsx";
import gridEmpty from "@/assets/grid_empty.png";
import starEmpty from "@/assets/star_tab_empty.svg";
import { useAppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { EmbeddedExplorerGrid } from "../embedded-explorer/EmbeddedExplorerGrid";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { InfiniteScroll } from "@/features/ui/components/infinite-scroll/InfiniteScroll";
import { useRouter } from "next/router";
import { DefaultRoute, getDefaultRouteId } from "@/utils/defaultRoutes";
import { useMemo } from "react";
import { canCreateChildren } from "@/features/items/utils";
import { Spinner } from "@gouvfr-lasuite/ui-kit";

/**
 * Wrapper around EmbeddedExplorerGrid to display a list of items in a table.
 *
 * It provides:
 * - Runtime tree lazy loading support
 *
 * TODO: Refactor using EmbeddedExplorer
 *
 */
export const AppExplorerGrid = () => {
  const { t } = useTranslation();
  const appExplorer = useAppExplorer();

  const router = useRouter();

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

  const effectiveOnNavigate = appExplorer.onNavigate ?? onNavigate;

  const handleFileClick = appExplorer.onFileClick ?? ((item: Item) => {
    if (item.url) {
      // We need to ensure the preview items list is updated when clicking on a file from the grid. Because this list
      // can be updated when clicking on a file from the search modal which sets the preview items to a list of one item.
      setPreviewItems(appExplorer.childrenItems ?? []);
      setPreviewItem(item);
    } else {
      addToast(<ToasterItem>{t("explorer.grid.no_url")}</ToasterItem>);
    }
  });

  const isLoading =
    appExplorer.isLoading || appExplorer.childrenItems === undefined;
  const isEmpty = appExplorer.childrenItems?.length === 0;

  const canAddChildren = item
    ? canCreateChildren(item, router.pathname)
    : false;

  const defaultRouteId = getDefaultRouteId(router.pathname);
  const emptyCTATranslationSuffix = useMemo(() => {
    if (defaultRouteId === DefaultRoute.MY_FILES) {
      return ".default";
    }
    if (defaultRouteId) {
      return `.${defaultRouteId}`.replaceAll("-", "_");
    }
    if (!canAddChildren) {
      return ".no_create";
    }
    return ".default";
  }, [defaultRouteId, canAddChildren]);

  const emptyCaptionTranslationSuffix = useMemo(() => {
    if (defaultRouteId) {
      return `.default`;
    }
    return ".folder";
  }, [defaultRouteId]);

  const getContent = () => {
    if (isEmpty) {
      return (
        <div className="c__datagrid__empty-placeholder fs-h3 clr-greyscale-900 fw-bold">
          <img
            src={
              defaultRouteId === DefaultRoute.FAVORITES
                ? starEmpty.src
                : gridEmpty.src
            }
            alt={t("components.datagrid.empty_alt")}
            className="explorer__grid__empty__image"
          />
          <div className="explorer__grid__empty">
            <div className="explorer__grid__empty__caption">
              {t(
                `explorer.grid.empty.caption${emptyCaptionTranslationSuffix}`,
              )}
            </div>
            <div className="explorer__grid__empty__cta">
              {t(`explorer.grid.empty.cta${emptyCTATranslationSuffix}`)}
            </div>
          </div>
        </div>
      );
    }

    if (!appExplorer.childrenItems) {
      return null;
    }

    const gridContent = (
      <EmbeddedExplorerGrid
        items={appExplorer.childrenItems}
        parentItem={item}
        gridActionsCell={appExplorer.gridActionsCell}
        onNavigate={effectiveOnNavigate}
        setRightPanelForcedItem={setRightPanelForcedItem}
        disableItemDragAndDrop={appExplorer.disableItemDragAndDrop}
        selectedItems={selectedItems}
        setSelectedItems={setSelectedItems}
        enableMetaKeySelection={true}
        displayMode={displayMode}
        canSelect={appExplorer.canSelect}
        onFileClick={handleFileClick}
        sortState={appExplorer.sortState}
        onSort={appExplorer.onSort}
        prefs={appExplorer.prefs}
        onChangeColumn={appExplorer.onChangeColumn}
        column1Config={appExplorer.column1Config}
        column2Config={appExplorer.column2Config}
      />
    );

    // If infinite scroll props are provided, wrap with InfiniteScroll
    if (
      appExplorer.hasNextPage !== undefined &&
      appExplorer.fetchNextPage
    ) {
      return (
        <InfiniteScroll
          hasNextPage={appExplorer.hasNextPage}
          isFetchingNextPage={appExplorer.isFetchingNextPage || false}
          fetchNextPage={appExplorer.fetchNextPage}
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
      {isLoading && (
        <div className="explorer__grid__loading-overlay">
          <Spinner size="xl" />
        </div>
      )}
    </div>
  );
};
