import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/app-view/ExplorerSearchButton";
import { useMutationCreateOdfDocument } from "../../hooks/useMutations";

type ExplorerTreeActionsProps = {
  openCreateFolderModal: () => void;
};

export const ExplorerTreeActions = ({
  openCreateFolderModal,
}: ExplorerTreeActionsProps) => {
  const { t } = useTranslation();
  const { treeIsInitialized, item, setPreviewItem, setPreviewItems } =
    useGlobalExplorer();
  const createOdfDocument = useMutationCreateOdfDocument();

  const createMenu = useDropdownMenu();
  const showMenu = item ? item?.abilities?.children_create : true;

  if (!treeIsInitialized) {
    return null;
  }

  const handleCreateOdf = (kind: "odt" | "ods" | "odp") => {
    const filename = t(`explorer.actions.createOdf.defaults.${kind}`);
    createOdfDocument.mutate(
      { parentId: item?.id, kind, filename },
      {
        onSuccess: (created) => {
          setPreviewItems([created]);
          setPreviewItem(created);
        },
      },
    );
  };

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
              label: t("explorer.actions.createOdf.actions.text"),
              value: "new-odt",
              isHidden: !showMenu,
              callback: () => handleCreateOdf("odt"),
            },
            {
              icon: <span className="material-icons">table_chart</span>,
              label: t("explorer.actions.createOdf.actions.spreadsheet"),
              value: "new-ods",
              isHidden: !showMenu,
              callback: () => handleCreateOdf("ods"),
            },
            {
              icon: <span className="material-icons">slideshow</span>,
              label: t("explorer.actions.createOdf.actions.slides"),
              value: "new-odp",
              isHidden: !showMenu,
              callback: () => handleCreateOdf("odp"),
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
