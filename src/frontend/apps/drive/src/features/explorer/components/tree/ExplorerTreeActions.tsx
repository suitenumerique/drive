import {
  DropdownMenu,
  IconSize,
  useDropdownMenu,
} from "@gouvfr-lasuite/ui-kit";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import createWorkspaceSvg from "@/assets/icons/create_workspace.svg";
import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/app-view/ExplorerSearchButton";
import { ItemIcon } from "../icons/ItemIcon";
import { Item, ItemType } from "@/features/drivers/types";
import { ExplorerCreateFileType } from "../modals/ExplorerCreateFileModal";

type ExplorerTreeActionsProps = {
  openCreateFolderModal: () => void;
  openCreateWorkspaceModal: () => void;
  openCreateFileModal: (type: ExplorerCreateFileType) => void;
};

export const ExplorerTreeActions = ({
  openCreateFolderModal,
  openCreateWorkspaceModal,
  openCreateFileModal,
}: ExplorerTreeActionsProps) => {
  const { t } = useTranslation();
  const { treeIsInitialized, item } = useGlobalExplorer();

  const createMenu = useDropdownMenu();

  const renderFileIcon = (item: Partial<Item>) => {
    return (
      <div>
        <ItemIcon item={item as Item} size={IconSize.MEDIUM} type="mini" />
      </div>
    );
  };

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
            {
              icon: renderFileIcon({
                type: ItemType.FILE,
                filename: "doc.odt",
                mimetype:
                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              }),
              label: t("explorer.tree.create.file.doc"),
              value: "info",
              isHidden: !item?.abilities?.children_create,
              callback: () => openCreateFileModal(ExplorerCreateFileType.DOC),
            },
            {
              icon: renderFileIcon({
                type: ItemType.FILE,
                filename: "powerpoint.odp",
                mimetype:
                  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
              }),
              label: t("explorer.tree.create.file.powerpoint"),
              value: "info",
              isHidden: !item?.abilities?.children_create,
              callback: () =>
                openCreateFileModal(ExplorerCreateFileType.POWERPOINT),
            },
            {
              icon: renderFileIcon({
                type: ItemType.FILE,
                filename: "calc.ods",
                mimetype:
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              }),
              label: t("explorer.tree.create.file.calc"),
              value: "info",
              isHidden: !item?.abilities?.children_create,
              callback: () => openCreateFileModal(ExplorerCreateFileType.CALC),
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
