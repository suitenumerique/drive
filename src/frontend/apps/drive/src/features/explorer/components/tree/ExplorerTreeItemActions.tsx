import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { Button, useModal } from "@openfun/cunningham-react";
import settingsSvg from "@/assets/icons/settings.svg";
import infoSvg from "@/assets/icons/info.svg";
import { useTranslation } from "react-i18next";
import { Item } from "@/features/drivers/types";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import clsx from "clsx";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import { WorkspaceShareModal } from "../modals/share/WorkspaceShareModal";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { useDeleteTreeNode } from "./hooks/useDeleteTreeNode";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import { ExplorerRenameItemModal } from "../modals/ExplorerRenameItemModal";
import { ExplorerMoveFolder } from "../modals/move/ExplorerMoveFolderModal";
import { getParentIdFromPath, isIdInItemTree } from "../../utils/utils";
import { useRouter } from "next/router";
import { useDeleteItem } from "../../hooks/useDeleteItem";

export type ExplorerTreeItemActionsProps = {
  item: Item;
};
export const ExplorerTreeItemActions = ({
  item,
}: ExplorerTreeItemActionsProps) => {
  const { t } = useTranslation();
  const menu = useDropdownMenu();
  const explorerContext = useGlobalExplorer();

  const { deleteItems } = useDeleteItem();
  const router = useRouter();
  const editWorkspaceModal = useModal();
  const shareWorkspaceModal = useModal();
  const isWorkspace = itemIsWorkspace(item);
  const { deleteTreeNode } = useDeleteTreeNode();
  const createFolderModal = useModal();
  const renameModal = useModal();
  const moveModal = useModal();

  // Simplified deletion logic for tree item actions
  const onDelete = async () => {
    await deleteItems([item.id]);

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
    menu.setIsOpen(false);

    if (redirectId) {
      router.push(`/explorer/items/${redirectId}`);
    }
  };

  return (
    <>
      <div
        className={clsx("explorer__tree__item__actions", {
          "explorer__tree__item__actions--open": menu.isOpen,
        })}
      >
        {!item.main_workspace && (
          <DropdownMenu
            options={[
              {
                icon: <img src={infoSvg.src} alt="" />,
                label: t("explorer.tree.workspace.options.info"),
                value: "info",
                isHidden: item.main_workspace,
                callback: () => {
                  explorerContext.setRightPanelForcedItem(item);
                  explorerContext.setRightPanelOpen(true);
                },
              },
              {
                icon: <span className="material-icons">group</span>,
                label: item.abilities.accesses_manage
                  ? t("explorer.tree.workspace.options.share")
                  : t("explorer.tree.workspace.options.share_view"),
                value: "share",
                isHidden: !isWorkspace || item.main_workspace,
                callback: shareWorkspaceModal.open,
              },
              {
                icon: <span className="material-icons">arrow_forward</span>,
                label: t("explorer.grid.actions.move"),
                value: "move",
                isHidden: !item.abilities.move,
                callback: moveModal.open,
              },
              {
                icon: <img src={settingsSvg.src} alt="" />,
                label: isWorkspace
                  ? t("explorer.tree.workspace.options.settings_workspace")
                  : t("explorer.grid.actions.rename"),
                value: "settings",
                isHidden: !item.abilities.update || item.main_workspace,
                callback: () => {
                  if (isWorkspace) {
                    editWorkspaceModal.open();
                  } else {
                    renameModal.open();
                  }
                },
              },
              {
                icon: <span className="material-icons">delete</span>,
                label: !isWorkspace
                  ? t("explorer.tree.workspace.options.delete_folder")
                  : t("explorer.tree.workspace.options.delete_workspace"),
                value: "delete",
                isHidden: !item.abilities.destroy || item.main_workspace,
                callback: onDelete,
              },
            ]}
            {...menu}
            onOpenChange={menu.setIsOpen}
          >
            <Button
              size="nano"
              variant="tertiary"
              aria-label="more_actions"
              className="explorer__tree__item__actions__button-more"
              onClick={() => menu.setIsOpen(true)}
              icon={<span className="material-icons more">more_horiz</span>}
            />
          </DropdownMenu>
        )}
        <Button
          size="nano"
          // color="primary"
          aria-label="add_children"
          className="explorer__tree__item__actions__button-add"
          icon={<span className="material-icons">add</span>}
          onClick={(e) => {
            e.stopPropagation();
            createFolderModal.open();
          }}
        ></Button>
      </div>
      {editWorkspaceModal.isOpen && (
        <ExplorerEditWorkspaceModal
          {...editWorkspaceModal}
          item={item as Item}
          onClose={() => {
            editWorkspaceModal.close();
          }}
        />
      )}
      {shareWorkspaceModal.isOpen && (
        <WorkspaceShareModal {...shareWorkspaceModal} item={item as Item} />
      )}
      {createFolderModal.isOpen && (
        <ExplorerCreateFolderModal {...createFolderModal} parentId={item.id} />
      )}

      {renameModal.isOpen && (
        <ExplorerRenameItemModal {...renameModal} item={item} key={item.id} />
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
