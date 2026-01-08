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
      "useGlobalExplorer must be used within an GlobalExplorerProvider"
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
        onLoadChildren={async (itemId, page) => {
          // Currently, we append a _X suffix at the end of favorite item IDs to differentiate them
          // when a node containing a favorite child is opened. This avoids duplicate IDs in the tree component,
          // which would otherwise cause errors. Therefore, we need to remove the _X suffix for API requests.
          const id = itemId.split("_")[0];
          if (id === DefaultRoute.FAVORITES) {
            const response = await driver.getFavoriteItems({
              page: page,
              type: ItemType.FOLDER,
            });

            const result = response.children.map((item) =>
              itemToTreeItem(item, id, true)
            ) as TreeViewDataType<Item>[];

            return {
              children: result,
              pagination: response.pagination,
            };
          }
          const data = await driver.getChildren(id, {
            page: page,
            type: ItemType.FOLDER,
          });
          const result = data.children.map((item) =>
            itemToTreeItem(item, id)
          ) as TreeViewDataType<Item>[];

          return {
            children: result,
            pagination: data.pagination,
          };
        }}
        onRefresh={async (id) => {
          const item = await driver.getItem(id);
          return itemToTreeItem(item) as TreeViewDataType<Item>;
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
        onSetPreviewItem={setPreviewItem}
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

  const treeContext = useTreeContext<TreeItem>();

  const initialTree = async () => {
    const items: TreeViewDataType<TreeItem>[] = [];

    const response = await getDriver().getFavoriteItems({
      page: 1,
      type: ItemType.FOLDER,
    });

    const favorites = response.children.map((item) =>
      itemToTreeItem(item, DefaultRoute.FAVORITES, true)
    ) as TreeViewDataType<Item>[];

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
    initialTree();
  }, []);

  return children;
};

export const itemToTreeItem = (
  item: Item,
  parentId?: string,
  isFavoriteItem?: boolean
): TreeItem => {
  const pathLevel = item.path.split(".").length - 1;
  // We add the path level to the id to avoid conflicts with the same id inside the tree.
  // This is useful when we have a favorite item that is a child of another item.
  const id = item.id + (isFavoriteItem ? `_${pathLevel}` : "");
  return {
    ...item,
    id,
    parentId: parentId,
    childrenCount: item.numchild_folder ?? 0,
    children:
      item.children?.map((child) =>
        itemToTreeItem(child, item.id, isFavoriteItem)
      ) ?? [],
    nodeType: TreeViewNodeTypeEnum.NODE,
    title: getItemTitle(item),
  };
};

export const itemsToTreeItems = (
  items: Item[],
  parentId?: string
): TreeItem[] => {
  return items.map((item) => itemToTreeItem(item, parentId));
};
