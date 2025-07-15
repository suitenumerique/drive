import { ItemType } from "@/features/drivers/types";
import { Item } from "@/features/drivers/types";
import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { itemToTreeItem, useGlobalExplorer } from "../GlobalExplorerContext";
import clsx from "clsx";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { Loader, useCunningham } from "@openfun/cunningham-react";
import gridEmpty from "@/assets/grid_empty.png";
import {
  AppExplorerProps,
  useAppExplorer,
} from "@/features/explorer/components/app-view/AppExplorer";
import { EmbeddedExplorerGrid } from "../embedded-explorer/EmbeddedExplorerGrid";

/**
 * ExplorerGridItems wrapper around ExplorerGridItems to display a list of items in a table.
 *
 * It provides:
 * - Runtime tree lazy loading support
 *
 * TODO: Refactor using ExplorerGridItemsExplorer
 *
 */
export const AppExplorerGrid = (props: AppExplorerProps) => {
  const { t } = useTranslation();
  const { t: tc } = useCunningham();

  const {
    setSelectedItems,
    selectedItems,
    treeIsInitialized,
    onNavigate,
    setRightPanelForcedItem,
    item,
    itemId,
    displayMode,
  } = useGlobalExplorer();

  const { filters, disableItemDragAndDrop } = useAppExplorer();
  const effectiveOnNavigate = props.onNavigate ?? onNavigate;
  const treeContext = useTreeContext();

  const folders = useMemo(() => {
    if (!props.childrenItems) {
      return [];
    }

    return props.childrenItems.filter((item) => item.type === ItemType.FOLDER);
  }, [props.childrenItems]);

  // Opens the item and its parents in the tree.
  useEffect(() => {
    if (treeIsInitialized && itemId) {
      treeContext?.treeApiRef.current?.open(itemId);
      treeContext?.treeApiRef.current?.openParents(itemId);
    }
  }, [itemId, treeIsInitialized]);

  // Sets the children of the item in the tree.
  useEffect(() => {
    const itemFilters = filters ?? {};

    if (!treeIsInitialized || !itemId || Object.keys(itemFilters).length > 0) {
      return;
    }

    // We merge the existing children with the new folders or we create the children
    const childrens = folders.map((folder) => {
      const folderNode = treeContext?.treeData.getNode(folder.id);
      if (folderNode) {
        const children = folderNode.children?.map((child) => child) as Item[];
        const item = itemToTreeItem({
          ...folder,
          children: children,
        });
        item.hasLoadedChildren =
          folder.numchild_folder !== undefined &&
          folder.numchild_folder > 0 &&
          children.length > 0;
        return item;
      } else {
        const children = itemToTreeItem({
          ...folder,
          children: [],
        });
        children.hasLoadedChildren = false;
        return children;
      }
    });

    treeContext?.treeData.setChildren(itemId, childrens);
  }, [folders, treeIsInitialized]);

  const isLoading = props.childrenItems === undefined;
  const isEmpty = props.childrenItems?.length === 0;
  const canCreateChildren = item?.abilities?.children_create;

  const getContent = () => {
    if (isLoading) {
      return <Loader aria-label={tc("components.datagrid.loader_aria")} />;
    }
    if (isEmpty) {
      return (
        <div className="c__datagrid__empty-placeholder fs-h3 clr-greyscale-900 fw-bold">
          <img src={gridEmpty.src} alt={t("components.datagrid.empty_alt")} />
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

    return (
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
      />
    );
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
