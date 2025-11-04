import { Item, ItemType } from "@/features/drivers/types";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useModal } from "@openfun/cunningham-react";
import { t } from "i18next";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import settingsSvg from "@/assets/icons/settings.svg";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ExplorerRenameItemModal } from "../modals/ExplorerRenameItemModal";
import { FileShareModal } from "../modals/share/FileShareModal";
import { WorkspaceShareModal } from "../modals/share/WorkspaceShareModal";
import { useDeleteItem } from "../../hooks/useDeleteItem";
import { ExplorerMoveFolder } from "../modals/move/ExplorerMoveFolderModal";
import { getParentIdFromPath, isIdInItemTree } from "../../utils/utils";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import { useDeleteTreeNode } from "../tree/hooks/useDeleteTreeNode";
import { useRouter } from "next/router";

export type ItemActionDropdownProps = {
  item: Item;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  trigger: React.ReactNode;
};

export const ItemActionDropdown = ({
  item,
  isOpen,
  setIsOpen,
  trigger,
}: ItemActionDropdownProps) => {
  const router = useRouter();
  const { setRightPanelForcedItem, setRightPanelOpen } = useGlobalExplorer();
  const isWorkspace = itemIsWorkspace(item);
  const { handleDownloadItem } = useDownloadItem();
  const { deleteItems: deleteItem } = useDeleteItem();
  const shareWorkspaceModal = useModal();
  const shareFileModal = useModal();
  const renameModal = useModal();
  const moveModal = useModal();
  const editWorkspaceModal = useModal();
  const explorerContext = useGlobalExplorer();
  const { deleteTreeNode } = useDeleteTreeNode();

  const canShareWorkspace = isWorkspace;
  const canShareFile = item.type === ItemType.FILE;
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
    const isWorkspace = itemIsWorkspace(item);
    const currentItemIsDeletedPath = isIdInItemTree(currentItem.path, item.id);

    // Determine the redirect target after deletion
    let redirectId: string | undefined;

    if (isWorkspace && currentItemIsDeletedPath) {
      // If deleting a workspace and the current item is part of the workspace tree, redirect to the main workspace
      redirectId = explorerContext.mainWorkspace?.id;
    } else if (
      currentItemIsDeletedPath ||
      (parentId && item.id === currentItem.id)
    ) {
      // If deleting an item in the current workspace or the current item itself, go to parent
      redirectId = parentId || explorerContext.mainWorkspace?.id;
    }

    deleteTreeNode(item.id, !!redirectId && redirectId === parentId);
    setIsOpen(false);

    if (redirectId) {
      router.push(`/explorer/items/${redirectId}`);
    }
  };

  return (
    <>
      <DropdownMenu
        options={[
          {
            icon: <span className="material-icons">info</span>,
            label: t("explorer.grid.actions.info"),
            value: "info",
            callback: () => {
              setRightPanelForcedItem(item);
              setRightPanelOpen(true);
            },
          },
          {
            icon: <span className="material-icons">group</span>,
            label: item.abilities?.accesses_manage
              ? t("explorer.tree.workspace.options.share")
              : t("explorer.tree.workspace.options.share_view"),
            isHidden: !canShareWorkspace,
            callback: shareWorkspaceModal.open,
          },
          {
            icon: <span className="material-icons">group</span>,
            label: item.abilities?.accesses_manage
              ? t("explorer.tree.workspace.options.share")
              : t("explorer.tree.workspace.options.share_view"),
            isHidden: !canShareFile,
            callback: shareFileModal.open,
          },
          {
            icon: <span className="material-icons">arrow_forward</span>,
            label: t("explorer.grid.actions.move"),
            isHidden: !item.abilities?.move,
            callback: handleMove,
          },
          {
            icon: <span className="material-icons">download</span>,
            label: t("explorer.grid.actions.download"),
            isHidden: item.type === ItemType.FOLDER,
            value: "download",
            showSeparator: true,
            callback: handleDownload,
          },
          {
            icon: <img src={settingsSvg.src} alt="" />,
            label: isWorkspace
              ? t("explorer.tree.workspace.options.settings_workspace")
              : t("explorer.grid.actions.rename"),
            isHidden: !item.abilities?.update || item.main_workspace,
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
            icon: <span className="material-icons">delete</span>,
            label: !isWorkspace
              ? t("explorer.tree.workspace.options.delete_folder")
              : t("explorer.tree.workspace.options.delete_workspace"),
            value: "delete",
            showSeparator: true,
            isHidden: !item.abilities?.destroy || item.main_workspace,
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
      {canShareWorkspace && shareWorkspaceModal.isOpen && (
        <WorkspaceShareModal
          {...shareWorkspaceModal}
          item={item}
          key={item.id}
        />
      )}
      {canShareFile && shareFileModal.isOpen && (
        <FileShareModal {...shareFileModal} item={item} key={item.id} />
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
