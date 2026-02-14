import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/app-view/ExplorerSearchButton";

type ExplorerTreeActionsProps = {
  openCreateFolderModal: () => void;
  openCreateFileModal: () => void;
};

export const ExplorerTreeActions = ({
  openCreateFolderModal,
  openCreateFileModal,
}: ExplorerTreeActionsProps) => {
  const { t } = useTranslation();
  const { treeIsInitialized, item } = useGlobalExplorer();

  const createMenu = useDropdownMenu();
  const showMenu = item ? item?.abilities?.children_create : true;

  if (!treeIsInitialized) {
    return null;
  }

  const handleCreateFile = () => openCreateFileModal();

  return (
    <div className="explorer__tree__actions">
      <div className="explorer__tree__actions__left">
        <DropdownMenu
          options={[
            {
              icon: <img src={createFolderSvg.src} alt="" />,
              label: t("explorer.actions.createFolder.modal.title"),
              value: "info",
              isHidden: !showMenu,
              callback: openCreateFolderModal,
            },
            {
              icon: <span className="material-icons">description</span>,
              label: t("explorer.actions.createFile.menu"),
              value: "new-file",
              isHidden: !showMenu,
              callback: handleCreateFile,
            },
          ]}
          {...createMenu}
          onOpenChange={createMenu.setIsOpen}
        >
          <Button
            icon={<span className="material-icons">add</span>}
            onClick={() => createMenu.setIsOpen(true)}
          >
            {t("explorer.tree.createFolder")}
          </Button>
        </DropdownMenu>
      </div>
      <ExplorerSearchButton keyboardShortcut />
    </div>
  );
};
