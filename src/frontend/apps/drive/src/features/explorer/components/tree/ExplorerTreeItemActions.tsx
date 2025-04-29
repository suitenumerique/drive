import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { Button, useModal } from "@openfun/cunningham-react";
import settingsSvg from "@/assets/icons/settings.svg";
import infoSvg from "@/assets/icons/info.svg";
import { useTranslation } from "react-i18next";
import { useMutationDeleteWorskpace } from "../../hooks/useMutations";
import { Item } from "@/features/drivers/types";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import clsx from "clsx";
import { useExplorer } from "../ExplorerContext";
import { WorkspaceShareModal } from "../modals/share/WorkspaceShareModal";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { useDeleteTreeNode } from "./hooks/useDeleteTreeNode";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
export type ExplorerTreeItemActionsProps = {
  item: Item;
};
export const ExplorerTreeItemActions = ({
  item,
}: ExplorerTreeItemActionsProps) => {
  const { t } = useTranslation();
  const menu = useDropdownMenu();
  const explorerContext = useExplorer();
  const deleteWorkspaceModal = useMutationDeleteWorskpace();
  const editWorkspaceModal = useModal();
  const shareWorkspaceModal = useModal();
  const isWorkspace = itemIsWorkspace(item);
  const { deleteTreeNode } = useDeleteTreeNode();
  const createFolderModal = useModal();

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
                icon: <img src={settingsSvg.src} alt="" />,
                label: t("explorer.tree.workspace.options.settings"),

                value: "settings",
                isHidden: !item.abilities.update || item.main_workspace,
                callback: editWorkspaceModal.open,
              },
              {
                icon: <span className="material-icons">delete</span>,
                label: t("explorer.tree.workspace.options.delete"),
                value: "delete",
                isHidden: !item.abilities.destroy || item.main_workspace,
                callback: () =>
                  deleteWorkspaceModal.mutate(item.id, {
                    onSuccess: () => {
                      deleteTreeNode(item.id);
                      menu.setIsOpen(false);
                    },
                  }),
              },
            ]}
            {...menu}
            onOpenChange={menu.setIsOpen}
          >
            <Button
              size="nano"
              color="tertiary-text"
              className="explorer__tree__item__actions__button-more"
              onClick={() => menu.setIsOpen(true)}
              icon={<span className="material-icons more">more_horiz</span>}
            />
          </DropdownMenu>
        )}
        <Button
          size="nano"
          color="primary"
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
    </>
  );
};
