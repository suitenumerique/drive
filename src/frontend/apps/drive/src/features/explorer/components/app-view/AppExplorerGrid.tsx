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
import { TreeViewDataType, useTreeContext } from "@gouvfr-lasuite/ui-kit";
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

  const updateTree = async () => {
    const tree = await driver.getTree(itemId);
    console.log("TREE", tree);

    const aux = (parent: TreeViewDataType<TreeItem>, children: Item[]) => {
      const childrens = itemsToTreeItems(children);
      treeContext?.treeData.setChildren(parent.id, childrens);
    };

    const root = treeContext?.treeData.getNode(tree.id);
    if (!root) {
      throw new Error("Root not found");
    }
    console.log("ROOT", root);
    aux(root, tree.children ?? []);
    // TODO: Remove this, ugly.
    setTimeout(() => {
      treeContext?.treeApiRef.current?.open(itemId);
      treeContext?.treeApiRef.current?.openParents(itemId);
    }, 100);
  };

  useEffect(() => {
    if (!treeIsInitialized || !itemId) {
      return;
    }
    const node = treeContext?.treeData.getNode(itemId);
    if (node) {
      return;
    }
    updateTree();
  }, [treeIsInitialized, itemId]);

  // Sets the children of the item in the tree.
  useEffect(() => {
    const itemFilters = filters ?? {};

    if (!treeIsInitialized || !itemId || Object.keys(itemFilters).length > 0) {
      return;
    }

    const node = treeContext?.treeData.getNode(itemId);
    if (node) {
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
    }
  }, [folders, treeIsInitialized]);

  const handleFileClick = (item: Item) => {
    if (item.url) {
      setPreviewItem(item);
    } else {
      addToast(<ToasterItem>{t("explorer.grid.no_url")}</ToasterItem>);
    }
  };

  // Set the preview files list.
  useEffect(() => {
    setPreviewItems(props.childrenItems ?? []);
  }, [props.childrenItems]);

  const isLoading = props.childrenItems === undefined;
  const isEmpty = props.childrenItems?.length === 0;
  const canCreateChildren = item?.abilities?.children_create;

  // const { data: tree } = useQuery({
  //   queryKey: ["tree", itemId],
  //   enabled: AmIInTree(),
  //   queryFn: () => {
  //     return getDriver().getTree(itemId!);
  //   },
  // });

  // useEffect(() => {
  //   if (!tree) {
  //     return;
  //   }
  //   // if (!treeItem) {
  //   //   return;
  //   // }
  //   // console.log("ITEM ID CHANGED", itemId);
  //   const node = treeContext?.treeData.getNode(itemId);
  //   console.log("NODE", node);
  //   if (node) {
  //     return;
  //   }

  //   // NOPE: ça cause une boucle car treeItem est rafraichit avant l'arbre, et l'arbre va être reconstruit avec initiaLId.
  //   // Et même si on modifiait pour que ça fonctionne, on perdrait tous les items en cache de l'arbre.
  //   // queryClient.invalidateQueries({ queryKey: ["initialTreeItem"] });

  //   const tree = driver.getTree(itemId);
  //   // Add LAZY TO TREE
  // }, [itemId, tree]);

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
