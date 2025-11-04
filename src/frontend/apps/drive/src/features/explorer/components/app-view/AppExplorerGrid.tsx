import { ItemType, TreeItem } from "@/features/drivers/types";
import { Item } from "@/features/drivers/types";
import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  itemsToTreeItems,
  itemToTreeItem,
  useGlobalExplorer,
} from "../GlobalExplorerContext";
import clsx from "clsx";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { Loader, useCunningham } from "@openfun/cunningham-react";
import gridEmpty from "@/assets/grid_empty.png";
import {
  AppExplorerProps,
  useAppExplorer,
} from "@/features/explorer/components/app-view/AppExplorer";
import { EmbeddedExplorerGrid } from "../embedded-explorer/EmbeddedExplorerGrid";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { getDriver } from "@/features/config/Config";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/Auth";

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
    treeIsInitialized,
    onNavigate,
    setRightPanelForcedItem,
    item,
    itemId,
    displayMode,
    setPreviewItem,
    setPreviewItems,
  } = useGlobalExplorer();

  const { filters, disableItemDragAndDrop } = useAppExplorer();
  const effectiveOnNavigate = props.onNavigate ?? onNavigate;
  const treeContext = useTreeContext<TreeItem>();
  const driver = getDriver();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const folders = useMemo(() => {
    if (!props.childrenItems) {
      return undefined;
    }

    return props.childrenItems.filter((item) => item.type === ItemType.FOLDER);
  }, [props.childrenItems]);

  const updateTree = async () => {
    const tree = await driver.getTree(itemId);
    const root = treeContext?.treeData.getNode(tree.id);
    if (!root) {
      // example: when landing on a public workspace, the public workspace is not
      // present in the root nodes yet. We need to add it. So by invalidating the firstLevelItems query,
      // the tree will be re-initialized with the public workspace inside TreeProviderInitializer.
      // ( The backend automatically adds the public workspace to the users root nodes if it is
      // the first time the user lands on a public workspace. That's why a seconds /items fetch will
      // contains the public workspace, but not the first time. ).
      // Special case: if the user is not logged in, we add the public workspace to the tree because subsequent /items
      // fetches won't contain the public workspace. So we need to add it that way to make sure the breadcrumbs works.
      if (user) {
        queryClient.invalidateQueries({ queryKey: ["firstLevelItems"] });
      } else {
        treeContext?.treeData.addRootNode(itemToTreeItem(tree));
      }
      return;
    }
    const childrens = itemsToTreeItems(tree.children ?? []);
    treeContext?.treeData.setChildren(root.id, childrens);
    // TODO: Remove this, ugly. But if I don't set this, the tree is not opened.
    setTimeout(() => {
      treeContext?.treeApiRef.current?.open(itemId);
      treeContext?.treeApiRef.current?.openParents(itemId);
    }, 100);
  };

  const updateChildren = () => {
    if (!folders) {
      return;
    }
    // We merge the existing children with the new folders or we create the children
    const childrens = folders.map((folder) => {
      const folderNode = treeContext?.treeData.getNode(folder.id);
      if (folderNode) {
        // What is the point of this ?
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
    treeContext?.treeApiRef.current?.open(itemId);
  };

  // Lazy loading of the children elements.
  useEffect(() => {
    if (!treeIsInitialized || !itemId) {
      return;
    }
    const node = treeContext?.treeData.getNode(itemId);
    if (!node) {
      return;
    }
    const itemFilters = filters ?? {};
    const hasFilters = Object.keys(itemFilters).length > 0;
    if (!hasFilters) {
      // Sets the children of the item in the tree.
      updateChildren();
    }
  }, [itemId, folders, treeIsInitialized]);

  // Handles loading /tree if needed.
  useEffect(() => {
    if (!treeIsInitialized || !itemId) {
      return;
    }
    const node = treeContext?.treeData.getNode(itemId);
    if (node) {
      return;
    }
    // Load /tree if the current node is not already loaded in the tree.
    // Example: can happen when clicking on a folder from the search modal.
    updateTree();
  }, [itemId, treeIsInitialized]);

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
        onFileClick={handleFileClick}
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
