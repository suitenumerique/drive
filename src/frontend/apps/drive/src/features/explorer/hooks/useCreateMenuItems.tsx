import { MenuItem, IconSize } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import uploadFileSvg from "@/assets/icons/upload_file.svg";
import uploadFolderSvg from "@/assets/icons/upload_folder.svg";
import { ItemIcon } from "../components/icons/ItemIcon";
import { Item, ItemType } from "@/features/drivers/types";
import {
  ExplorerCreateFileModal,
  ExplorerCreateFileType,
} from "../components/modals/ExplorerCreateFileModal";
import { ExplorerCreateFolderModal } from "../components/modals/ExplorerCreateFolderModal";
import { useModal } from "@gouvfr-lasuite/cunningham-react";
import { useState } from "react";

type UseCreateMenuItemsProps = {
  includeImport?: boolean;
  includeCreate?: boolean;
};

type UseCreateMenuItemsReturn = {
  menuItems: MenuItem[];
  modals: React.ReactNode;
};

const renderFileIcon = (item: Partial<Item>) => {
  return (
    <div>
      <ItemIcon item={item as Item} size={IconSize.MEDIUM} type="mini" />
    </div>
  );
};

export const useCreateMenuItems = ({
  includeImport = false,
  includeCreate = true,
}: UseCreateMenuItemsProps = {}): UseCreateMenuItemsReturn => {
  const { t } = useTranslation();
  const { item, itemId } = useGlobalExplorer();
  const canCreateChildren = item ? item?.abilities?.children_create : true;
  const isHidden = !canCreateChildren;

  const createFolderModal = useModal();
  const [createFileModalType, setCreateFileModalType] =
    useState<ExplorerCreateFileType>(ExplorerCreateFileType.DOC);
  const createFileModal = useModal();

  const openCreateFileModal = (type: ExplorerCreateFileType) => {
    setCreateFileModalType(type);
    createFileModal.open();
  };

  const items: MenuItem[] = [
    {
      icon: <img src={createFolderSvg.src} alt="" />,
      label: t("explorer.tree.create.folder"),
      isHidden,
      callback: createFolderModal.open,
    },
    { type: "separator" },
  ];

  if (includeImport) {
    items.push(
      {
        icon: <img src={uploadFileSvg.src} alt="" />,
        label: t("explorer.tree.import.files"),
        isHidden,
        callback: () => {
          document.getElementById("import-files")?.click();
        },
      },
      {
        icon: <img src={uploadFolderSvg.src} alt="" />,
        label: t("explorer.tree.import.folders"),
        isHidden,
        callback: () => {
          document.getElementById("import-folders")?.click();
        },
      },
      { type: "separator" },
    );
  }

  if (includeCreate) {
    items.push(
      {
        icon: renderFileIcon({
          type: ItemType.FILE,
          filename: "doc.odt",
          mimetype:
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }),
        label: t("explorer.tree.create.file.doc"),
        isHidden,
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
        isHidden,
        callback: () => openCreateFileModal(ExplorerCreateFileType.POWERPOINT),
      },
      {
        icon: renderFileIcon({
          type: ItemType.FILE,
          filename: "calc.ods",
          mimetype:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
        label: t("explorer.tree.create.file.calc"),
        isHidden,
        callback: () => openCreateFileModal(ExplorerCreateFileType.CALC),
      },
    );
  }

  const modals = (
    <>
      <ExplorerCreateFolderModal {...createFolderModal} parentId={itemId} />
      <ExplorerCreateFileModal
        {...createFileModal}
        parentId={itemId}
        type={createFileModalType}
      />
    </>
  );

  return { menuItems: items, modals };
};
