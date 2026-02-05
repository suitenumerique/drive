import {
  SetStateAction,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Dispatch } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Item,
  ItemBreadcrumb,
  ItemType,
  TreeItem,
} from "@/features/drivers/types";
import { createContext } from "react";
import { getDriver } from "@/features/config/Config";
import { Toaster } from "@/features/ui/components/toaster/Toaster";
import { useDropzone } from "react-dropzone";
import { useUploadZone } from "../hooks/useUpload";

import {
  TreeProvider,
  TreeViewDataType,
  TreeViewNodeTypeEnum,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { ExplorerDndProvider } from "./ExplorerDndProvider";
import { useFirstLevelItems } from "../hooks/useQueries";
import { useTranslation } from "react-i18next";
import { getItemTitle } from "../utils/utils";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";

import { useAuth } from "@/features/auth/Auth";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { CustomFilesPreview } from "@/features/ui/preview/custom-files-preview/CustomFilesPreview";

export interface GlobalExplorerContextType {
  displayMode: "sdk" | "app";
  selectedItems: Item[];
  selectedItemsMap: Record<string, Item>;
  mainWorkspace: Item | undefined;
  setSelectedItems: Dispatch<SetStateAction<Item[]>>;
  itemId: string;
  item: Item | undefined;
  firstLevelItems: Item[] | undefined;
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
  setPreviewItem: (item: Item | undefined) => void;
  setPreviewItems: (items: Item[]) => void;
  isMinimalLayout?: boolean;
  refreshMobileNodes: () => void;
  mobileNodesRefreshTrigger: number;
}

export const GlobalExplorerContext = createContext<
  GlobalExplorerContextType | undefined
>(undefined);

export const useGlobalExplorer = () => {
  const context = useContext(GlobalExplorerContext);
  if (!context) {
    throw new Error(
      "useGlobalExplorer must be used within an GlobalExplorerProvider",
    );
  }
  return context;
};

export enum NavigationEventType {
  ITEM,
}

export type NavigationEvent = {
  type: NavigationEventType.ITEM;
  item: NavigationItem;
};

export type NavigationItem = Item | ItemBreadcrumb | TreeItem;

interface ExplorerProviderProps {
  children: React.ReactNode;
  displayMode: "sdk" | "app";
  itemId: string;
  onNavigate: (event: NavigationEvent) => void;
}

/**
 * - Handles the selection of items
 * - Handles the right panel states
 * - Handles the left panel states
 * - Sets TreeProvider
 * - Sets ExplorerDndProvider
 * - Sets Toaster
 *
 * Behavior:
 *
 * We first try to request the current item if it exists, if so, we enable the
 * next queries ( /tree and /items ). We don't start all the queries at once just
 * to make sure the item is accessible. If the item is not accessible, the backend
 * returns 401 or 403 errors and the we let the handler redirect to the 401 or 403 page.
 */
export const GlobalExplorerProvider = ({
  children,
  displayMode = "app",
  itemId,
  onNavigate,
}: ExplorerProviderProps) => {
  const driver = getDriver();
  const { user } = useAuth();

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
  const [isInitialized, setIsInitialized] = useState<boolean>(false);
  const [treeIsInitialized, setTreeIsInitialized] = useState<boolean>(false);
  const [mobileNodesRefreshTrigger, setMobileNodesRefreshTrigger] = useState(0);

  /**
   * Triggers a refresh of the mobile nodes.
   * We do this as a hack because we can't act the same as we do with the desktop tree because the tree is imperative not reactive.
   */
  const refreshMobileNodes = () => {
    setMobileNodesRefreshTrigger((prev) => prev + 1);
  };

  const { data: item } = useQuery({
    queryKey: ["items", itemId],
    queryFn: () => getDriver().getItem(itemId),
    enabled: !!itemId,
  });

  useEffect(() => {
    if (isInitialized) {
      return;
    }
    if (!initialId) {
      setIsInitialized(true);
      return;
    }
    if (item) {
      setIsInitialized(true);
    }
  }, [item]);

  const { data: firstLevelItems } = useFirstLevelItems();

  const mainWorkspace = useMemo(() => {
    if (user && user.main_workspace) {
      return user.main_workspace;
    }

    return firstLevelItems?.find((item) => item.main_workspace);
  }, [firstLevelItems, user]);

  useEffect(() => {
    // If we open the right panel and we have a selection, we need to clear it.
    if (rightPanelForcedItem?.id === itemId) {
      setSelectedItems([]);
    }
  }, [rightPanelForcedItem]);

  /**
   * We need to force the current folder to be displayed in the right panel.
   */
  useEffect(() => {
    if (rightPanelOpen) {
      setSelectedItems([]);
    }
  }, [rightPanelOpen]);

  const { dropZone } = useUploadZone({ item: item! });

  /**
   * Preview states.
   */
  const [previewItem, setPreviewItem] = useState<Item | undefined>(undefined);
  const [previewItems, setPreviewItems] = useState<Item[]>([]);


  return (
    <GlobalExplorerContext.Provider
      value={{
        treeIsInitialized,
        setTreeIsInitialized,
        firstLevelItems,
        displayMode,
        selectedItems,
        selectedItemsMap,
        mainWorkspace,
        setSelectedItems,
        itemId,
        initialId,
        item,
        onNavigate,
        dropZone,
        rightPanelForcedItem,
        setRightPanelForcedItem,
        rightPanelOpen,
        setRightPanelOpen,
        isLeftPanelOpen,
        setIsLeftPanelOpen,
        setPreviewItem,
        setPreviewItems,
        refreshMobileNodes,
        mobileNodesRefreshTrigger,
      }}
    >
      <TreeProvider
        initialTreeData={[]}
        initialNodeId={initialId}
        onLoadChildren={async (treeId, page) => {
          // Extract the original item ID from the tree ID for API requests.
          // Tree IDs for favorites follow the format: `parentTreeId::itemId` (e.g., `favorites::abc123`)
          const originalId = getOriginalIdFromTreeId(treeId);
          const isFavoriteItem = treeId.startsWith(DefaultRoute.FAVORITES);

          if (originalId === DefaultRoute.FAVORITES) {
            const response = await driver.getFavoriteItems({
              page: page,
              type: ItemType.FOLDER,
            });

            const result = response.children.map((item) =>
              itemToTreeItem(item, treeId, true),
            ) as TreeViewDataType<Item>[];

            return {
              children: result,
              pagination: response.pagination,
            };
          }
          const data = await driver.getChildren(originalId, {
            page: page,
            type: ItemType.FOLDER,
          });
          const result = data.children.map((item) =>
            itemToTreeItem(item, treeId, isFavoriteItem),
          ) as TreeViewDataType<Item>[];

          return {
            children: result,
            pagination: data.pagination,
          };
        }}
        onRefresh={async (treeId) => {
          const originalId = getOriginalIdFromTreeId(treeId);
          const isFavoriteItem = treeId.startsWith(DefaultRoute.FAVORITES);
          const item = await driver.getItem(originalId);
          // Extract parent tree ID from current tree ID
          const parentTreeId = treeId.includes("::")
            ? treeId.substring(0, treeId.lastIndexOf("::"))
            : undefined;
          return itemToTreeItem(
            item,
            parentTreeId,
            isFavoriteItem,
          ) as TreeViewDataType<Item>;
        }}
      >
        <TreeProviderInitializer>
          <ExplorerDndProvider>
            {isInitialized ? children : <SpinnerPage />}
          </ExplorerDndProvider>
        </TreeProviderInitializer>
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
      <CustomFilesPreview
        currentItem={previewItem}
        items={previewItems}
        setPreviewItem={setPreviewItem}
        onItemsChange={setPreviewItems}
      />
    </GlobalExplorerContext.Provider>
  );
};

/**
 * Initializes the tree provider with the root items ( aka workspaces )
 */
const TreeProviderInitializer = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const { setTreeIsInitialized } = useGlobalExplorer();
  const { t } = useTranslation();
  const { user } = useAuth();

  const treeContext = useTreeContext<TreeItem>();

  const initialTree = async () => {
    const items: TreeViewDataType<TreeItem>[] = [];

    const response = await getDriver().getFavoriteItems({
      page: 1,
      type: ItemType.FOLDER,
    });

    const favorites = response.children.map((item) =>
      itemToTreeItem(item, DefaultRoute.FAVORITES, true),
    );

    const favoritesNode: TreeViewDataType<TreeItem> = {
      id: DefaultRoute.FAVORITES,
      nodeType: TreeViewNodeTypeEnum.SIMPLE_NODE,
      childrenCount: favorites.length,
      children: favorites,
      label: t("explorer.tree.favorites"),
      pagination: response.pagination,
    };

    items.push(favoritesNode);
    treeContext?.treeData.resetTree(items);
    setTreeIsInitialized(true);
  };

  // TODO: Move to global tree context?
  useEffect(() => {
    if (!user) {
      return;
    }

    initialTree();
  }, [user]);

  return children;
};

/**
 * Generates a unique tree ID based on the parent tree ID and the original item ID.
 * This ensures uniqueness even when the same item appears multiple times in the tree
 * (e.g., once in favorites and once as a child of an opened favorite folder).
 *
 * Format: `{parentTreeId}::{itemId}` for favorite items, or just `{itemId}` for non-favorite items.
 *
 * @param originalId - The original item ID
 * @param parentTreeId - The parent's tree ID (which may already contain the path)
 * @param isFavoriteItem - Whether this item is in the favorites branch
 * @returns A unique tree ID
 */
export const generateTreeId = (
  originalId: string,
  parentTreeId?: string,
  isFavoriteItem?: boolean,
): string => {
  if (!isFavoriteItem) {
    return originalId;
  }
  // For favorite items, build a path-based ID to ensure uniqueness
  return parentTreeId ? `${parentTreeId}::${originalId}` : originalId;
};

/**
 * Extracts the original item ID from a tree ID.
 * The tree ID format is `{parentTreeId}::{itemId}` for favorites, or just `{itemId}` for non-favorites.
 *
 * @param treeId - The tree ID to extract from
 * @returns The original item ID
 */
export const getOriginalIdFromTreeId = (treeId: string): string => {
  const parts = treeId.split("::");
  return parts[parts.length - 1];
};

export const itemToTreeItem = (
  item: Item,
  parentTreeId?: string,
  isFavoriteItem?: boolean,
): TreeItem => {
  const originalId = item.id;
  const treeId = generateTreeId(originalId, parentTreeId, isFavoriteItem);

  return {
    ...item,
    id: treeId,
    originalId,
    parentId: parentTreeId,
    childrenCount: item.numchild_folder ?? 0,
    children:
      item.children?.map((child) =>
        itemToTreeItem(child, treeId, isFavoriteItem),
      ) ?? [],
    nodeType: TreeViewNodeTypeEnum.NODE,
    title: getItemTitle(item),
  };
};

export const itemsToTreeItems = (
  items: Item[],
  parentId?: string,
): TreeItem[] => {
  return items.map((item) => itemToTreeItem(item, parentId));
};
