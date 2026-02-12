import { Item, ItemType } from "@/features/drivers/types";
import { DropdownMenu, useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { useModal } from "@gouvfr-lasuite/cunningham-react";
import { t } from "i18next";
import { itemToTreeItem, useGlobalExplorer } from "../GlobalExplorerContext";
import settingsSvg from "@/assets/icons/settings.svg";
import starredSvg from "@/assets/icons/starred.svg";
import unstarredSvg from "@/assets/icons/starred-slash.svg";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ExplorerRenameItemModal } from "../modals/ExplorerRenameItemModal";
import { ItemShareModal } from "../modals/share/ItemShareModal";
import { useDeleteItem } from "../../hooks/useDeleteItem";
import { ExplorerMoveFolder } from "../modals/move/ExplorerMoveFolderModal";
import { getParentIdFromPath, setManualNavigationItemId } from "../../utils/utils";
import { useRouter } from "next/router";
import { useEffect } from "react";
import {
  useMutationCreateFavoriteItem,
  useMutationDeleteFavoriteItem,
} from "../../hooks/useMutations";
import { DefaultRoute } from "@/utils/defaultRoutes";

export type ItemActionDropdownProps = {
  item: Item;
  itemId?: string;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  trigger: React.ReactNode;
  onModalOpenChange?: (isModalOpen: boolean) => void;
  minimal?: boolean;
};

export const ItemActionDropdown = ({
  item,
  itemId,
  isOpen,
  setIsOpen,
  trigger,
  onModalOpenChange,
  minimal = false,
}: ItemActionDropdownProps) => {
  const router = useRouter();
  const { setRightPanelForcedItem, setRightPanelOpen } = useGlobalExplorer();
  const effectiveItemId = itemId ?? item.originalId ?? item.id;
  const effectiveItem = { ...item, id: effectiveItemId };

  const { handleDownloadItem } = useDownloadItem();
  const { deleteItems: deleteItem } = useDeleteItem();
  const treeContext = useTreeContext();
  const shareItemModal = useModal();

  const renameModal = useModal();
  const moveModal = useModal();

  const explorerContext = useGlobalExplorer();

  const { mutateAsync: deleteFavoriteItem } = useMutationDeleteFavoriteItem();
  const { mutateAsync: createFavoriteItem } = useMutationCreateFavoriteItem();
  const canViewShareModal = item.abilities?.accesses_view;

  const handleMove = () => {
    moveModal.open();
  };

  const handleDownload = async () => {
    handleDownloadItem(item);
  };

  const handleDelete = async () => {
    await deleteItem([effectiveItemId]);
    const currentItem = explorerContext.item;
    if (!currentItem) return;

    const parentId = getParentIdFromPath(item.path);

    // Determine the redirect target after deletion
    const redirectId: string | undefined = parentId;

    if (redirectId) {
      setManualNavigationItemId(redirectId);
      router.push(`/explorer/items/${redirectId}`);
    } else {
      router.push(`/explorer/items/my-files`);
    }
  };

  const handleFavorite = async () => {
    await createFavoriteItem(effectiveItemId, {
      onSuccess: () => {
        // Generate a unique tree ID for the favorite item
        const itemTree = itemToTreeItem(item, DefaultRoute.FAVORITES, true);
        treeContext?.treeData.addChild(DefaultRoute.FAVORITES, itemTree);
      },
    });
  };

  const handleUnfavorite = async () => {
    await deleteFavoriteItem(effectiveItemId);
  };

  useEffect(() => {
    onModalOpenChange?.(
      renameModal.isOpen || shareItemModal.isOpen || moveModal.isOpen,
    );
  }, [renameModal.isOpen, shareItemModal.isOpen, moveModal.isOpen]);

  return (
    <>
      <DropdownMenu
        options={[
          {
            icon: <span className="material-icons">info</span>,
            label: t("explorer.item.actions.view_info"),
            value: "info",
            isHidden: minimal,
            callback: () => {
              setRightPanelForcedItem(item);
              setRightPanelOpen(true);
            },
          },
          {
            icon: <span className="material-icons">group</span>,
            label: t("explorer.item.actions.share"),
            isHidden: !item.abilities?.accesses_view,
            callback: shareItemModal.open,
          },

          {
            icon: <span className="material-icons">arrow_forward</span>,
            label: t("explorer.item.actions.move"),
            isHidden: !item.abilities?.move || minimal,
            callback: handleMove,
          },
          {
            icon: <span className="material-icons">download</span>,
            label: t("explorer.item.actions.download"),
            isHidden: item.type === ItemType.FOLDER || minimal,
            value: "download",
            showSeparator: true,
            callback: handleDownload,
          },
          {
            icon: <img src={settingsSvg.src} alt="" />,
            label: t("explorer.item.actions.rename"),
            isHidden: !item.abilities?.update,
            value: "edit",
            callback: () => {
              renameModal.open();
            },
            showSeparator: true,
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
            value: "favorite",
            isHidden: !item.abilities?.retrieve,
            callback: item.is_favorite ? handleUnfavorite : handleFavorite,
          },
          {
            icon: <span className="material-icons">delete</span>,
            label: t("explorer.item.actions.delete"),
            value: "delete",
            showSeparator: true,
            isHidden:
              !item.abilities?.destroy || item.main_workspace || minimal,
            callback: handleDelete,
          },
        ]}
        isOpen={isOpen}
        onOpenChange={setIsOpen}
      >
        {trigger}
      </DropdownMenu>
      {renameModal.isOpen && (
        <ExplorerRenameItemModal
          {...renameModal}
          item={effectiveItem}
          key={effectiveItemId}
        />
      )}
      {canViewShareModal && shareItemModal.isOpen && (
        <ItemShareModal
          {...shareItemModal}
          item={effectiveItem}
          key={effectiveItemId}
        />
      )}

      {moveModal.isOpen && (
        <ExplorerMoveFolder
          {...moveModal}
          itemsToMove={[effectiveItem]}
          key={effectiveItemId}
          initialFolderId={getParentIdFromPath(effectiveItem.path)}
        />
      )}
    </>
  );
};
