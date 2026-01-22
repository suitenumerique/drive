import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/app-view/ExplorerSearchButton";
import { isMyFilesRoute } from "@/utils/defaultRoutes";
import { useRouter } from "next/router";

type ExplorerTreeActionsProps = {
  openCreateFolderModal: () => void;
};

export const ExplorerTreeActions = ({
  openCreateFolderModal,
}: ExplorerTreeActionsProps) => {
  const { t } = useTranslation();
  const { treeIsInitialized, item } = useGlobalExplorer();
  const router = useRouter();
  const isMyFiles = isMyFilesRoute(router.pathname);
  const createMenu = useDropdownMenu();
  const showMenu = isMyFiles || item?.abilities?.children_create;

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
              isHidden: !showMenu,
              callback: openCreateFolderModal,
            },
          ]}
          {...createMenu}
          onOpenChange={createMenu.setIsOpen}
        >
          <Button
            disabled={!showMenu}
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
