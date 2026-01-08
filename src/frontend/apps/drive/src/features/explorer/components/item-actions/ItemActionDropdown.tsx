import { Item, ItemType } from "@/features/drivers/types";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { DropdownMenu, useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { useModal } from "@gouvfr-lasuite/cunningham-react";
import { t } from "i18next";
import { itemToTreeItem, useGlobalExplorer } from "../GlobalExplorerContext";
import settingsSvg from "@/assets/icons/settings.svg";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ExplorerRenameItemModal } from "../modals/ExplorerRenameItemModal";
import { ItemShareModal } from "../modals/share/ItemShareModal";
import { useDeleteItem } from "../../hooks/useDeleteItem";
import { ExplorerMoveFolder } from "../modals/move/ExplorerMoveFolderModal";
import { getParentIdFromPath } from "../../utils/utils";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import { useRouter } from "next/router";
import { useEffect } from "react";
import {
  useMutationCreateFavoriteItem,
  useMutationDeleteFavoriteItem,
} from "../../hooks/useMutations";
import { DefaultRoute } from "@/utils/defaultRoutes";

export type ItemActionDropdownProps = {
  item: Item;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  trigger: React.ReactNode;
  onModalOpenChange?: (isModalOpen: boolean) => void;
  minimal?: boolean;
};

export const ItemActionDropdown = ({
  item,
  isOpen,
  setIsOpen,
  trigger,
  onModalOpenChange,
  minimal = false,
}: ItemActionDropdownProps) => {
  const router = useRouter();
  const { setRightPanelForcedItem, setRightPanelOpen } = useGlobalExplorer();
  const isWorkspace = itemIsWorkspace(item);

  const { handleDownloadItem } = useDownloadItem();
  const { deleteItems: deleteItem } = useDeleteItem();
  const treeContext = useTreeContext();
  const shareItemModal = useModal();

  const renameModal = useModal();
  const moveModal = useModal();
  const editWorkspaceModal = useModal();
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
    await deleteItem([item.id]);
    const currentItem = explorerContext.item;
    if (!currentItem) return;

    const parentId = getParentIdFromPath(item.path);

    // Determine the redirect target after deletion
    const redirectId: string | undefined = parentId;

    if (redirectId) {
      router.push(`/explorer/items/${redirectId}`);
    } else {
      router.push(`/explorer/items/my_files`);
    }
  };

  const handleFavorite = async () => {
    await createFavoriteItem(item.id, {
      onSuccess: () => {
        // We add the path level to the id to avoid conflicts with the same id inside the tree for favorite items.
        const id = item.id + "_0";
        const itemTree = itemToTreeItem({ ...item, id }, undefined);
        treeContext?.treeData.addChild(DefaultRoute.FAVORITES, itemTree);
      },
    });
  };

  const handleUnfavorite = async () => {
    await deleteFavoriteItem(item.id);
  };

  useEffect(() => {
    onModalOpenChange?.(
      renameModal.isOpen ||
        shareItemModal.isOpen ||
        editWorkspaceModal.isOpen ||
        moveModal.isOpen
    );
  }, [
    renameModal.isOpen,
    shareItemModal.isOpen,
    editWorkspaceModal.isOpen,
    moveModal.isOpen,
  ]);

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
              if (isWorkspace) {
                editWorkspaceModal.open();
              } else {
                renameModal.open();
              }
            },
            showSeparator: true,
          },
          {
            icon: <span className="material-icons">favorite</span>,
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
        <ExplorerRenameItemModal {...renameModal} item={item} key={item.id} />
      )}
      {canViewShareModal && shareItemModal.isOpen && (
        <ItemShareModal {...shareItemModal} item={item} key={item.id} />
      )}

      {editWorkspaceModal.isOpen && (
        <ExplorerEditWorkspaceModal
          {...editWorkspaceModal}
          item={item as Item}
          onClose={() => {
            editWorkspaceModal.close();
          }}
        />
      )}
      {moveModal.isOpen && (
        <ExplorerMoveFolder
          {...moveModal}
          itemsToMove={[item]}
          key={item.id}
          initialFolderId={getParentIdFromPath(item.path)}
        />
      )}
    </>
  );
};
