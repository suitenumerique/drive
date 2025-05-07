import {
  SetStateAction,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Dispatch } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  displayMode: "sdk" | "app";
  selectedItems: Item[];
  selectedItemsMap: Record<string, Item>;
  setSelectedItems: Dispatch<SetStateAction<Item[]>>;
  itemId: string;
  item: Item | undefined;
  firstLevelItems: Item[] | undefined;
  items: Item[] | undefined;
  tree: Item | null | undefined;
  onNavigate: (event: NavigationEvent) => void;
  initialId: string | undefined;
  treeIsInitialized: boolean;
  setTreeIsInitialized: (isInitialized: boolean) => void;
  dropZone: ReturnType<typeof useDropzone>;
  rightPanelForcedItem?: Item;
  setRightPanelForcedItem: (item: Item | undefined) => void;
  rightPanelOpen: boolean;
  setRightPanelOpen: (open: boolean) => void;
  isLeftPanelOpen: boolean;
  setIsLeftPanelOpen: (isLeftPanelOpen: boolean) => void;
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

interface ExplorerProviderProps {
  children: React.ReactNode;
  displayMode: "sdk" | "app";
  itemId: string;
  onNavigate: (event: NavigationEvent) => void;
}

export const ExplorerProvider = ({
  children,
  displayMode = "app",
  itemId,
  onNavigate,
}: ExplorerProviderProps) => {
  const driver = getDriver();

  const queryClient = useQueryClient();
  const [selectedItems, setSelectedItems] = useState<Item[]>([]);

  // Avoid inifinite rerendering
  const selectedItemsMap = useMemo(() => {
    const map: Record<string, Item> = {};
    selectedItems.forEach((item) => {
      map[item.id] = item;
    });
    return map;
  }, [selectedItems]);

  const [rightPanelForcedItem, setRightPanelForcedItem] = useState<Item>();
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [isLeftPanelOpen, setIsLeftPanelOpen] = useState(false);

  const [initialId] = useState<string | undefined>(itemId);
  const [treeIsInitialized, setTreeIsInitialized] = useState<boolean>(false);

  const { data: items } = useQuery({
    queryKey: ["items"],
    queryFn: () => getDriver().getItems(),
  });

  const { data: item } = useQuery({
    queryKey: ["items", itemId],
    queryFn: () => getDriver().getItem(itemId),
    enabled: !!itemId,
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
    // The logic behind is simple: we want to execute the tree query ONLY if the first url is an
    // item url. Otherwise, it is not needed to perform the query because no there is no current
    // item ( like on the /trash page ). Even when landing first on /trash page, the tree will be
    // constructed during further navigation, so no need to perform the tree request too.
    enabled: !!initialId,
    queryFn: () => {
      return getDriver().getTree(initialId!);
    },
  });

  useEffect(() => {
    // If we open the right panel and we have a selection, we need to clear it.
    if (rightPanelForcedItem?.id === itemId) {
      setSelectedItems([]);
    }
  }, [rightPanelForcedItem]);

  /**
   * When the right panel is open, we need to force the new item to be displayed in the right panel.
   */
  useEffect(() => {
    if (item && rightPanelOpen) {
      setRightPanelForcedItem(item);
      setSelectedItems([]);
    }
  }, [item, rightPanelOpen]);

  const { dropZone } = useUploadZone({ item: item! });

  return (
    <ExplorerContext.Provider
      value={{
        treeIsInitialized,
        setTreeIsInitialized,
        firstLevelItems,
        displayMode,
        selectedItems,
        selectedItemsMap,
        setSelectedItems,
        itemId,
        initialId,
        item,
        items,
        tree,
        onNavigate,
        dropZone,
        rightPanelForcedItem,
        setRightPanelForcedItem,
        rightPanelOpen,
        setRightPanelOpen,
        isLeftPanelOpen,
        setIsLeftPanelOpen,
      }}
    >
      <TreeProvider
        initialTreeData={[]}
        initialNodeId={initialId}
        onLoadChildren={async (id) => {
          const children = await driver.getChildren(id, {
            type: ItemType.FOLDER,
          });

          queryClient.setQueryData(["items", id, "children"], children);
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
