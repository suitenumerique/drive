import { Item, ItemType } from "@/features/drivers/types";
import { useTreeContext, MenuItem } from "@gouvfr-lasuite/ui-kit";
import { useModal } from "@gouvfr-lasuite/cunningham-react";
import { t } from "i18next";
import {
  itemToTreeItem,
  useGlobalExplorer,
} from "../components/GlobalExplorerContext";
import settingsSvg from "@/assets/icons/settings.svg";
import starredSvg from "@/assets/icons/starred.svg";
import unstarredSvg from "@/assets/icons/starred-slash.svg";
import uploadFileSvg from "@/assets/icons/upload_file.svg";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ExplorerRenameItemModal } from "../components/modals/ExplorerRenameItemModal";
import { ExplorerCreateFolderModal } from "../components/modals/ExplorerCreateFolderModal";
import { NewFolderIcon } from "@/features/ui/components/icon/NewFolderIcon";
import { ItemShareModal } from "../components/modals/share/ItemShareModal";
import { useDeleteItem } from "./useDeleteItem";
import { ExplorerMoveFolder } from "../components/modals/move/ExplorerMoveFolderModal";
import { getParentIdFromPath, setManualNavigationItemId } from "../utils/utils";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import {
  useMutationCreateFavoriteItem,
  useMutationDeleteFavoriteItem,
} from "./useMutations";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { ModalRecursiveEncrypt } from "@/features/encryption/ModalRecursiveEncrypt";
import { ModalRecursiveRemoveEncryption } from "@/features/encryption/ModalRecursiveRemoveEncryption";
import { ModalEncryptionNotRoot } from "@/features/encryption/ModalEncryptionNotRoot";

type UseItemActionMenuItemsOptions = {
  onModalOpenChange?: (isModalOpen: boolean) => void;
};

type UseItemActionMenuItemsReturn = {
  getMenuItems: (
    item: Item,
    options?: { minimal?: boolean; itemId?: string; allowCreate?: boolean },
  ) => MenuItem[];
  modals: React.ReactNode;
  isModalOpen: boolean;
};

export const useItemActionMenuItems = ({
  onModalOpenChange,
}: UseItemActionMenuItemsOptions = {}): UseItemActionMenuItemsReturn => {
  const router = useRouter();
  const { setRightPanelForcedItem, setRightPanelOpen, ...explorerContext } =
    useGlobalExplorer();
  const { handleDownloadItem } = useDownloadItem();
  const { deleteItems: deleteItem } = useDeleteItem();
  const treeContext = useTreeContext();

  const { mutateAsync: deleteFavoriteItem } = useMutationDeleteFavoriteItem();
  const { mutateAsync: createFavoriteItem } = useMutationCreateFavoriteItem();

  const shareItemModal = useModal();
  const renameModal = useModal();
  const moveModal = useModal();
  const createFolderModal = useModal();
  const encryptModal = useModal();
  const removeEncryptionModal = useModal();

  const [currentItem, setCurrentItem] = useState<Item | null>(null);

  const isModalOpen =
    renameModal.isOpen ||
    shareItemModal.isOpen ||
    moveModal.isOpen ||
    createFolderModal.isOpen ||
    encryptModal.isOpen ||
    removeEncryptionModal.isOpen;

  useEffect(() => {
    onModalOpenChange?.(isModalOpen);
  }, [isModalOpen]);

  const handleFavorite = async (effectiveItemId: string, item: Item) => {
    await createFavoriteItem(effectiveItemId, {
      onSuccess: () => {
        if (item.type !== ItemType.FOLDER) {
          return;
        }
        const itemTree = itemToTreeItem(item, DefaultRoute.FAVORITES, true);
        treeContext?.treeData.addChild(DefaultRoute.FAVORITES, itemTree);
      },
    });
  };

  const handleUnfavorite = async (effectiveItemId: string) => {
    await deleteFavoriteItem(effectiveItemId);
  };

  const handleDelete = async (effectiveItemId: string, item: Item) => {
    await deleteItem([effectiveItemId]);
    const currentExplorerItem = explorerContext.item;
    if (!currentExplorerItem) return;

    const parentId = getParentIdFromPath(item.path);
    const redirectId: string | undefined = parentId;

    if (redirectId) {
      setManualNavigationItemId(redirectId);
      router.push(`/explorer/items/${redirectId}`);
    } else {
      router.push(`/explorer/items/my-files`);
    }
  };

  const getMenuItems = (
    item: Item,
    options?: { minimal?: boolean; itemId?: string; allowCreate?: boolean },
  ): MenuItem[] => {
    const minimal = options?.minimal ?? false;
    const allowCreate = options?.allowCreate ?? false;
    const effectiveItemId = options?.itemId ?? item.originalId ?? item.id;
    const effectiveItem = { ...item, id: effectiveItemId };
    const showAddChildren = allowCreate;

    return [
      ...(showAddChildren
        ? [
            {
              icon: <NewFolderIcon />,
              label: t("explorer.actions.createFolder.modal.title"),
              callback: () => {
                setCurrentItem(effectiveItem);
                createFolderModal.open();
              },
            },
            {
              icon: <img src={uploadFileSvg.src} alt="" />,
              label: t("explorer.tree.import.files"),
              callback: () => {
                document.getElementById("import-files")?.click();
              },
            },
            { type: "separator" as const },
          ]
        : []),

      {
        icon: <span className="material-icons">group</span>,
        label: t("explorer.item.actions.share"),
        isHidden: !item.abilities?.accesses_view,
        callback: () => {
          setCurrentItem(effectiveItem);
          shareItemModal.open();
        },
      },
      {
        icon: <span className="material-icons">download</span>,
        label: t("explorer.item.actions.download"),
        isHidden: item.type === ItemType.FOLDER || minimal,
        callback: () => {
          handleDownloadItem(item);
        },
      },

      {
        icon: (
          <img
            src={item.is_favorite ? unstarredSvg.src : starredSvg.src}
            alt=""
          />
        ),
        label: item.is_favorite
          ? t("explorer.item.actions.unfavorite")
          : t("explorer.item.actions.favorite"),
        isHidden: !item.abilities?.retrieve,
        callback: item.is_favorite
          ? () => handleUnfavorite(effectiveItemId)
          : () => handleFavorite(effectiveItemId, item),
      },
      { type: "separator" },
      {
        icon: <img src={settingsSvg.src} alt="" />,
        label: t("explorer.item.actions.rename"),
        isHidden: !item.abilities?.update,
        callback: () => {
          setCurrentItem(effectiveItem);
          renameModal.open();
        },
      },
      {
        icon: <span className="material-icons">arrow_forward</span>,
        label: t("explorer.item.actions.move"),
        isHidden: !item.abilities?.move || minimal,
        callback: () => {
          setCurrentItem(effectiveItem);
          moveModal.open();
        },
      },
      { type: "separator" },
      ...(!item.is_encrypted && item.abilities?.encrypt
        ? [
            {
              icon: <span className="material-icons">lock</span>,
              label: t("explorer.item.actions.encrypt", "Encrypt"),
              callback: () => {
                setCurrentItem(effectiveItem);
                encryptModal.open();
              },
            },
          ]
        : []),
      ...(item.is_encrypted && item.abilities?.remove_encryption
        ? [
            {
              icon: <span className="material-icons">lock_open</span>,
              label: t(
                "explorer.item.actions.remove_encryption",
                "Remove encryption",
              ),
              callback: () => {
                setCurrentItem(effectiveItem);
                removeEncryptionModal.open();
              },
            },
          ]
        : []),
      { type: "separator" },
      {
        icon: <span className="material-icons">info</span>,
        label: t("explorer.item.actions.view_info"),
        isHidden: minimal,
        callback: () => {
          setRightPanelForcedItem(item);
          setRightPanelOpen(true);
        },
      },
      { type: "separator" },
      {
        icon: <span className="material-icons">delete</span>,
        label: t("explorer.item.actions.delete"),
        variant: "danger" as const,
        isHidden: !item.abilities?.destroy || item.main_workspace || minimal,
        callback: () => handleDelete(effectiveItemId, item),
      },
    ];
  };

  const modals = (
    <>
      {currentItem && renameModal.isOpen && (
        <ExplorerRenameItemModal
          {...renameModal}
          item={currentItem}
          key={currentItem.id}
        />
      )}
      {currentItem &&
        currentItem.abilities?.accesses_view &&
        shareItemModal.isOpen && (
          <ItemShareModal
            {...shareItemModal}
            item={currentItem}
            key={currentItem.id}
          />
        )}
      {currentItem && moveModal.isOpen && (
        <ExplorerMoveFolder
          {...moveModal}
          itemsToMove={[currentItem]}
          key={currentItem.id}
          initialFolderId={getParentIdFromPath(currentItem.path)}
        />
      )}
      {currentItem && createFolderModal.isOpen && (
        <ExplorerCreateFolderModal
          {...createFolderModal}
          parent={currentItem}
        />
      )}
      {currentItem && encryptModal.isOpen && (
        <ModalRecursiveEncrypt
          isOpen
          onClose={encryptModal.close}
          item={currentItem}
        />
      )}
      {currentItem &&
        removeEncryptionModal.isOpen &&
        (currentItem.is_encrypted &&
        (!currentItem.is_encryption_root ||
          currentItem.is_inside_encrypted_subtree) ? (
          <ModalEncryptionNotRoot
            isOpen
            onClose={removeEncryptionModal.close}
            item={currentItem}
          />
        ) : (
          <ModalRecursiveRemoveEncryption
            isOpen
            onClose={removeEncryptionModal.close}
            item={currentItem}
          />
        ))}
    </>
  );

  return { getMenuItems, modals, isModalOpen };
};
