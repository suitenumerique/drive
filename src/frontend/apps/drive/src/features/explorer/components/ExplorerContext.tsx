import { SetStateAction, useContext, useEffect, useRef, useState } from "react";
import { Dispatch } from "react";
import { useQuery } from "@tanstack/react-query";
import { Item, ItemTreeItem, ItemType } from "@/features/drivers/types";
import { createContext } from "react";
import { getDriver } from "@/features/config/Config";
import {
  TreeApi,
  TreeDataItem,
  TreeViewNodeTypeEnum,
  useTree,
} from "@gouvfr-lasuite/ui-kit";
import { ExplorerDndProvider } from "./ExplorerDndProvider";
export interface ExplorerContextType {
  treeObject: ReturnType<typeof useTree<ItemTreeItem>>;
  selectedItemIds: Record<string, boolean>;
  setSelectedItemIds: Dispatch<SetStateAction<Record<string, boolean>>>;
  displayMode: "sdk" | "app";
  selectedItems: Item[];
  itemId: string;
  item: Item | undefined;
  firstLevelItems: Item[] | undefined;
  children: Item[] | undefined;
  tree: Item | undefined;
  onNavigate: (event: NavigationEvent) => void;
  initialId: string | undefined;
  treeApiRef?: React.RefObject<TreeApi<TreeDataItem<ItemTreeItem>> | undefined>;
}

export const ExplorerContext = createContext<ExplorerContextType | undefined>(
  undefined
);

export const useExplorer = () => {
  const context = useContext(ExplorerContext);
  if (!context) {
    throw new Error("useExplorer must be used within an ExplorerProvider");
  }
  return context;
};

export enum NavigationEventType {
  ITEM,
}

export type NavigationEvent = {
  type: NavigationEventType.ITEM;
  item: Item | ItemTreeItem;
};

export const ExplorerProvider = ({
  children,
  displayMode = "app",
  itemId,
  onNavigate,
}: {
  children: React.ReactNode;
  displayMode: "sdk" | "app";
  itemId: string;
  onNavigate: (event: NavigationEvent) => void;
}) => {
  const driver = getDriver();
  const ref = useRef<TreeApi<TreeDataItem<ItemTreeItem>>>(undefined);
  const [selectedItemIds, setSelectedItemIds] = useState<
    Record<string, boolean>
  >({});

  const [initialId, setInitialId] = useState<string | undefined>(itemId);

  const treeObject = useTree<ItemTreeItem>(
    [],
    async (id) => {
      const item = await driver.getItem(id);
      return itemToTreeItem(item);
    },
    async (id) => {
      const children = await driver.getChildren(id, ItemType.FOLDER);
      return children.map(itemToTreeItem);
    }
  );

  const handleNavigate = async (event: NavigationEvent) => {
    onNavigate(event);
    // const parentId = treeObject.getParentId(event.item.id);

    // if (parentId) {
    //   await treeObject.handleLoadChildren(parentId as string);
    //   ref.current?.openParents(parentId as string);
    // }
  };
  useEffect(() => {
    if (!initialId) {
      setInitialId(itemId);
    }
  }, [itemId]);

  const { data: item } = useQuery({
    queryKey: ["items", itemId],
    queryFn: () => getDriver().getItem(itemId),
  });

  const { data: itemChildren } = useQuery({
    queryKey: ["items", itemId, "children"],
    queryFn: () => getDriver().getChildren(itemId),
  });

  const { data: firstLevelItems } = useQuery({
    queryKey: ["firstLevelItems"],
    queryFn: () => getDriver().getItems(),
  });

  const { data: tree } = useQuery({
    queryKey: ["items", initialId, "tree"],
    refetchOnWindowFocus: false,
    queryFn: () => {
      if (!initialId) {
        return undefined;
      }
      return getDriver().getTree(initialId);
    },
  });

  const getSelectedItems = () => {
    return itemChildren
      ? itemChildren.filter((item) => selectedItemIds[item.id])
      : [];
  };

  return (
    <ExplorerContext.Provider
      value={{
        treeObject,
        selectedItemIds,
        setSelectedItemIds,
        firstLevelItems,
        displayMode,
        selectedItems: getSelectedItems(),
        itemId,
        initialId,
        item,
        tree,
        children: itemChildren,
        onNavigate: handleNavigate,
        treeApiRef: ref,
      }}
    >
      <ExplorerDndProvider>{children}</ExplorerDndProvider>
    </ExplorerContext.Provider>
  );
};

export const itemToTreeItem = (item: Item, parentId?: string): ItemTreeItem => {
  return {
    ...item,
    parentId: parentId,
    childrenCount: item.numchild_folder ?? 0,
    children: item.children?.map((child) => itemToTreeItem(child, item.id)),
    nodeType: TreeViewNodeTypeEnum.NODE,
  };
};

export const itemsToTreeItems = (
  items: Item[],
  parentId?: string
): ItemTreeItem[] => {
  return items.map((item) => itemToTreeItem(item, parentId));
};
