import {
  SetStateAction,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Dispatch } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Item,
  ItemType,
  ItemUploadState,
  TreeItem,
  WorkspaceType,
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
import { getItemTitle, getWorkspaceType } from "../utils/utils";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";
import { ItemInfo } from "@/features/items/components/ItemInfo";
import {
  FilePreview,
  FilePreviewType,
} from "@/features/ui/preview/files-preview/FilesPreview";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";

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
  item: Item | TreeItem;
};

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
  const { t } = useTranslation();
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
  const [isInitialized, setIsInitialized] = useState<boolean>(false);
  const [treeIsInitialized, setTreeIsInitialized] = useState<boolean>(false);
  const { handleDownloadItem } = useDownloadItem();

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
    return firstLevelItems?.find((item) => item.main_workspace);
  }, [firstLevelItems]);

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
  const previewFiles = useMemo(() => {
    return previewItems
      .filter((item) => item.type === ItemType.FILE)
      .map((item) => ({
        id: item.id,
        title: item.title,
        mimetype: item.mimetype ?? "",
        url: item.url ?? "",
        isSuspicious: item.upload_state === ItemUploadState.SUSPICIOUS,
      }));
  }, [previewItems]);

  const handleClosePreview = () => {
    setPreviewItem(undefined);
  };

  const handleChangePreviewItem = (file?: FilePreviewType) => {
    const item = previewItems.find((item) => file?.id === item.id);
    setPreviewItem(item);
  };

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
      <FilePreview
        isOpen={!!previewItem}
        onClose={handleClosePreview}
        title={t("file_preview.title")}
        files={previewFiles}
        onChangeFile={handleChangePreviewItem}
        handleDownloadFile={() => handleDownloadItem(previewItem)}
        openedFileId={previewItem?.id}
        sidebarContent={previewItem && <ItemInfo item={previewItem} />}
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
  const { firstLevelItems, setTreeIsInitialized } = useGlobalExplorer();
  const { t } = useTranslation();

  const treeContext = useTreeContext<TreeItem>();

  // TODO: Move to global tree context?
  useEffect(() => {
    if (!firstLevelItems) {
      return;
    }
    const firstLevelItems_: Item[] = firstLevelItems ?? [];

    const firstLevelTreeItems_: TreeItem[] = itemsToTreeItems(firstLevelItems_);
    const items: TreeViewDataType<TreeItem>[] = [];

    const getWorkspacesByType = (type: WorkspaceType) => {
      return firstLevelTreeItems_.filter((item) => {
        return getWorkspaceType(item as Item) === type;
      });
    };

    const mainWorkspaces = getWorkspacesByType(WorkspaceType.MAIN);

    // Arriving on a public workspace, we don't have any main workspace.
    if (mainWorkspaces.length > 0) {
      const mainWorkspace = mainWorkspaces[0] as Item;
      // We start to build the tree
      const personalWorkspaceNode: TreeViewDataType<TreeItem> = {
        id: "PERSONAL_SPACE",
        nodeType: TreeViewNodeTypeEnum.TITLE,
        headerTitle: t("explorer.tree.personalSpace"),
      };
      // We add the personal workspace node and the main workspace node
      items.push(personalWorkspaceNode);
      items.push(mainWorkspace);
    }

    const sharedWorkspaces = getWorkspacesByType(WorkspaceType.SHARED);
    const publicWorkspaces = getWorkspacesByType(WorkspaceType.PUBLIC);

    if (sharedWorkspaces.length > 0) {
      // We add a separator and the shared space node
      const separator: TreeViewDataType<TreeItem> = {
        id: "SEPARATOR",
        nodeType: TreeViewNodeTypeEnum.SEPARATOR,
      };

      const sharedSpace: TreeViewDataType<TreeItem> = {
        id: "SHARED_SPACE",
        nodeType: TreeViewNodeTypeEnum.TITLE,
        headerTitle: t("explorer.tree.shared_space"),
      };

      items.push(separator);
      items.push(sharedSpace);
      items.push(...sharedWorkspaces);
    }

    if (publicWorkspaces.length > 0) {
      const separator: TreeViewDataType<TreeItem> = {
        id: "SEPARATOR_PUBLIC",
        nodeType: TreeViewNodeTypeEnum.SEPARATOR,
      };
      const publicSpace: TreeViewDataType<TreeItem> = {
        id: "PUBLIC_SPACE",
        nodeType: TreeViewNodeTypeEnum.TITLE,
        headerTitle: t("explorer.tree.public_space"),
      };
      items.push(separator);
      items.push(publicSpace);
      items.push(...publicWorkspaces);
    }

    treeContext?.treeData.resetTree(items);
    setTreeIsInitialized(true);
  }, [firstLevelItems]);

  return children;
};

export const itemToTreeItem = (item: Item, parentId?: string): TreeItem => {
  return {
    ...item,
    parentId: parentId,
    childrenCount: item.numchild_folder ?? 0,
    children:
      item.children?.map((child) => itemToTreeItem(child, item.id)) ?? [],
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
