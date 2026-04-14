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
import { useRouter } from "next/router";
import { isMyFilesRoute } from "@/utils/defaultRoutes";

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
  const router = useRouter();
  const isOnMyFiles = isMyFilesRoute(router.pathname);
  const canCreateHere = item?.abilities?.children_create ?? false;
  const effectiveParentId = canCreateHere ? itemId : undefined;
  // On "My files", the item is created without a parent, which already puts
  // it in the current view — no redirect needed.
  const shouldRedirectToCreated = !canCreateHere && !isOnMyFiles;

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
      callback: createFolderModal.open,
    },
    { type: "separator" },
  ];

  if (includeImport) {
    items.push(
      {
        icon: <img src={uploadFileSvg.src} alt="" />,
        label: t("explorer.tree.import.files"),
        callback: () => {
          document.getElementById("import-files")?.click();
        },
      },
      {
        icon: <img src={uploadFolderSvg.src} alt="" />,
        label: t("explorer.tree.import.folders"),
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
        callback: () => openCreateFileModal(ExplorerCreateFileType.CALC),
      },
    );
  }

  const modals = (
    <>
      <ExplorerCreateFolderModal
        {...createFolderModal}
        parentId={effectiveParentId}
        redirectAfterCreate={shouldRedirectToCreated}
      />
      <ExplorerCreateFileModal
        {...createFileModal}
        parentId={effectiveParentId}
        redirectAfterCreate={shouldRedirectToCreated}
        type={createFileModalType}
      />
    </>
  );

  return { menuItems: items, modals };
};
