import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useExplorer } from "../ExplorerContext";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import createWorkspaceSvg from "@/assets/icons/create_workspace.svg";
import uploadFileSvg from "@/assets/icons/upload_file.svg";
import uploadFolderSvg from "@/assets/icons/upload_folder.svg";
import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

type ExplorerTreeActionsProps = {
  openCreateFolderModal: () => void;
  openCreateWorkspaceModal: () => void;
};

export const ExplorerTreeActions = ({
  openCreateFolderModal,
  openCreateWorkspaceModal,
}: ExplorerTreeActionsProps) => {
  const { t } = useTranslation();
  const { treeIsInitialized } = useExplorer();
  const importMenu = useDropdownMenu();
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

        <DropdownMenu
          options={[
            {
              icon: <img src={uploadFileSvg.src} alt="" />,
              label: t("explorer.tree.import.files"),
              value: "info",
              callback: () => {
                document.getElementById("import-files")?.click();
              },
            },
            {
              icon: <img src={uploadFolderSvg.src} alt="" />,
              label: t("explorer.tree.import.folders"),
              value: "info",
              callback: () => {
                document.getElementById("import-folders")?.click();
              },
            },
          ]}
          {...importMenu}
          onOpenChange={importMenu.setIsOpen}
        >
          <Button color="secondary" onClick={() => importMenu.setIsOpen(true)}>
            {t("explorer.tree.import.label")}
          </Button>
        </DropdownMenu>
      </div>
      <Button
        color="primary-text"
        aria-label={t("explorer.tree.search")}
        icon={<span className="material-icons">search</span>}
      />
    </div>
  );
};
