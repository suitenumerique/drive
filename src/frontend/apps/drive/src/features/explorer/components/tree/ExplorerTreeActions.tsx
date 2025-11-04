import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import createWorkspaceSvg from "@/assets/icons/create_workspace.svg";
import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/app-view/ExplorerSearchButton";

type ExplorerTreeActionsProps = {
  openCreateFolderModal: () => void;
  openCreateWorkspaceModal: () => void;
};

export const ExplorerTreeActions = ({
  openCreateFolderModal,
  openCreateWorkspaceModal,
}: ExplorerTreeActionsProps) => {
  const { t } = useTranslation();
  const { treeIsInitialized, item } = useGlobalExplorer();

  const createMenu = useDropdownMenu();

  if (!treeIsInitialized) {
    return null;
  }
  return (
    <div className="explorer__tree__actions">
      <div className="explorer__tree__actions__left">
        <DropdownMenu
          options={[
            {
              icon: <img src={createFolderSvg.src} alt="" />,
              label: t("explorer.tree.create.folder"),
              value: "info",
              isHidden: !item?.abilities?.children_create,
              callback: openCreateFolderModal,
            },
            {
              icon: <img src={createWorkspaceSvg.src} alt="" />,
              label: t("explorer.tree.create.workspace"),
              value: "info",
              callback: openCreateWorkspaceModal,
            },
          ]}
          {...createMenu}
          onOpenChange={createMenu.setIsOpen}
        >
          <Button
            icon={<span className="material-icons">add</span>}
            onClick={() => createMenu.setIsOpen(true)}
          >
            {t("explorer.tree.create.label")}
          </Button>
        </DropdownMenu>
      </div>
      <ExplorerSearchButton keyboardShortcut />
    </div>
  );
};
