import {
  DropdownMenu,
  TreeViewNodeTypeEnum,
  useDropdownMenu,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { Button, useModal } from "@openfun/cunningham-react";
import settingsSvg from "@/assets/icons/settings.svg";
import infoSvg from "@/assets/icons/info.svg";
import { useTranslation } from "react-i18next";
import { useMutationDeleteWorskpace } from "../../hooks/useMutations";
import { Item, TreeItem } from "@/features/drivers/types";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import clsx from "clsx";
import { useExplorer } from "../ExplorerContext";
import { useRouter } from "next/router";
export type ExplorerTreeItemActionsProps = {
  item: Item;
};
export const ExplorerTreeItemActions = ({
  item,
}: ExplorerTreeItemActionsProps) => {
  const { t } = useTranslation();
  const menu = useDropdownMenu();
  const treeContext = useTreeContext<TreeItem>();
  const explorerContext = useExplorer();
  const router = useRouter();
  const deleteWorkspaceModal = useMutationDeleteWorskpace();
  const editWorkspaceModal = useModal();
  return (
    <>
      <div
        className={clsx("explorer__tree__item__actions", {
          "explorer__tree__item__actions--open": menu.isOpen,
        })}
      >
        <div>
          <DropdownMenu
            options={[
              {
                icon: <img src={infoSvg.src} alt="" />,
                label: t("explorer.tree.workspace.options.info"),
                value: "info",
                callback: () => {
                  explorerContext.setRightPanelForcedItem(item);
                  explorerContext.setRightPanelOpen(true);
                },
              },
              {
                icon: <img src={settingsSvg.src} alt="" />,
                label: t("explorer.tree.workspace.options.settings"),
                value: "settings",
                callback: editWorkspaceModal.open,
              },
              {
                icon: <span className="material-icons">delete</span>,
                label: t("explorer.tree.workspace.options.delete"),
                value: "delete",
                callback: () =>
                  deleteWorkspaceModal.mutate(item.id, {
                    onSuccess: () => {
                      const node = treeContext?.treeData.getNode(item.id);
                      if (node) {
                        treeContext?.treeData.deleteNode(item.id);

                        //
                        if (node.nodeType === TreeViewNodeTypeEnum.NODE) {
                          const parentId = node.parentId;
                          if (parentId) {
                            router.push(`/explorer/items/${parentId}`);
                          }
                        }
                      }
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
              onClick={() => menu.setIsOpen(true)}
              icon={<span className="material-icons more">more_horiz</span>}
            />
          </DropdownMenu>
        </div>
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
    </>
  );
};
