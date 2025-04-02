import { SetStateAction, useContext, useEffect, useState } from "react";
import { Dispatch } from "react";
import { useQuery } from "@tanstack/react-query";
import { Item, ItemType, TreeItem } from "@/features/drivers/types";
import { createContext } from "react";
import { getDriver } from "@/features/config/Config";
import { Toaster } from "@/features/ui/components/toaster/Toaster";
import { useDropzone } from "react-dropzone";
import { useUploadZone } from "../hooks/useUpload";

import {
  TreeProvider,
  TreeViewDataType,
  TreeViewNodeTypeEnum,
} from "@gouvfr-lasuite/ui-kit";
import { ExplorerDndProvider } from "./ExplorerDndProvider";
export interface ExplorerContextType {
  selectedItemIds: Record<string, boolean>;
  setSelectedItemIds: Dispatch<SetStateAction<Record<string, boolean>>>;
  displayMode: "sdk" | "app";
  selectedItems: Item[];
  itemId: string;
  item: Item | undefined;
  firstLevelItems: Item[] | undefined;
  items: Item[] | undefined;
  children: Item[] | undefined;
  tree: Item | undefined;
  onNavigate: (event: NavigationEvent) => void;
  initialId: string | undefined;
  treeIsInitialized: boolean;
  setTreeIsInitialized: (isInitialized: boolean) => void;
  dropZone: ReturnType<typeof useDropzone>;
  rightPanelForcedItem?: Item;
  setRightPanelForcedItem: (item: Item | undefined) => void;
  rightPanelOpen: boolean;
  setRightPanelOpen: (open: boolean) => void;
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
  item: Item | TreeItem;
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

  const [selectedItemIds, setSelectedItemIds] = useState<
    Record<string, boolean>
  >({});
  const [rightPanelForcedItem, setRightPanelForcedItem] = useState<Item>();
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  const [initialId, setInitialId] = useState<string | undefined>(itemId);
  const [treeIsInitialized, setTreeIsInitialized] = useState<boolean>(false);

  useEffect(() => {
    // if the initialId is not set, we set it to the itemId to initialize the tree
    if (!initialId) {
      setInitialId(itemId);
    }
  }, [itemId, initialId]);

  const { data: items } = useQuery({
    queryKey: ["items"],
    queryFn: () => getDriver().getItems(),
  });

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
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    queryFn: () => getDriver().getItems(),
  });

  const { data: tree } = useQuery({
    queryKey: ["initialTreeItem", initialId],
    refetchOnWindowFocus: false,
    refetchOnMount: false,
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

  useEffect(() => {
    // If the right panel item is the same as the current item, we need to clear the selected items because the right panel
    // will be open and we don't want to show the selected items in the right panel
    if (!rightPanelForcedItem || rightPanelForcedItem.id === itemId) {
      setSelectedItemIds({});
    } else {
      setSelectedItemIds({ [rightPanelForcedItem.id]: true });
    }
  }, [rightPanelForcedItem]);

  const { dropZone } = useUploadZone({ item: item! });

  return (
    <ExplorerContext.Provider
      value={{
        selectedItemIds,
        setSelectedItemIds,
        treeIsInitialized,
        setTreeIsInitialized,
        firstLevelItems,
        displayMode,
        selectedItems: getSelectedItems(),
        itemId,
        initialId,
        item,
        items,
        tree,
        children: itemChildren,
        onNavigate,
        dropZone,
        rightPanelForcedItem,
        setRightPanelForcedItem,
        rightPanelOpen,
        setRightPanelOpen,
      }}
    >
      <TreeProvider
        initialTreeData={[]}
        initialNodeId={initialId}
        onLoadChildren={async (id) => {
          const children = await driver.getChildren(id, {
            type: ItemType.FOLDER,
          });
          const result = children.map((item) =>
            itemToTreeItem(item, id)
          ) as TreeViewDataType<Item>[];

          return result;
        }}
        onRefresh={async (id) => {
          const item = await driver.getItem(id);
          return itemToTreeItem(item) as TreeViewDataType<Item>;
        }}
      >
        <ExplorerDndProvider>{children}</ExplorerDndProvider>
      </TreeProvider>
      <input
        {...dropZone.getInputProps({
          webkitdirectory: "true",
          id: "import-folders",
        })}
      />
      <input
        {...dropZone.getInputProps({
          id: "import-files",
        })}
      />

      <Toaster />
    </ExplorerContext.Provider>
  );
};

export const itemToTreeItem = (item: Item, parentId?: string): TreeItem => {
  return {
    ...item,
    parentId: parentId,
    childrenCount: item.numchild_folder ?? 0,
    children:
      item.children?.map((child) => itemToTreeItem(child, item.id)) ?? [],
    nodeType: TreeViewNodeTypeEnum.NODE,
  };
};

export const itemsToTreeItems = (
  items: Item[],
  parentId?: string
): TreeItem[] => {
  return items.map((item) => itemToTreeItem(item, parentId));
};
