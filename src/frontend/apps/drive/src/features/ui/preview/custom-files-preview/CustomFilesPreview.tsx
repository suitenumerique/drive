import { Item, ItemType } from "@/features/drivers/types";
import { FilePreview, FilePreviewType } from "../files-preview/FilesPreview";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import { itemToPreviewFile } from "@/features/explorer/utils/utils";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ItemInfo } from "@/features/items/components/ItemInfo";
import { Button, useModal } from "@gouvfr-lasuite/cunningham-react";
import { ItemShareModal } from "@/features/explorer/components/modals/share/ItemShareModal";
import { useRefreshItemCache } from "@/features/explorer/hooks/useRefreshItems";

type CustomFilesPreviewProps = {
  currentItem?: Item;
  items: Item[];
  setPreviewItem?: (item?: Item) => void;
  /** Used for optimistic updates only ( when the file is renamed in the preview ) */
  onItemsChange?: (items: Item[]) => void;
};

export const CustomFilesPreview = ({
  currentItem,
  items,
  setPreviewItem,
  onItemsChange,
}: CustomFilesPreviewProps) => {
  const { t } = useTranslation();

  const { handleDownloadItem } = useDownloadItem();

  const files = useMemo(() => {
    return items
      .filter((item) => item.type === ItemType.FILE)
      .map(itemToPreviewFile);
  }, [items]);

  const handleClosePreview = () => {
    setPreviewItem?.(undefined);
  };

  const handleChangePreviewItem = (file?: FilePreviewType) => {
    const item = items.find((item) => file?.id === item.id);
    setPreviewItem?.(item);
  };


  const refreshItemCache = useRefreshItemCache();
  const handleFileRename = (file: FilePreviewType, newName: string) => {
    // Optimistic update of the items in the preview.
    onItemsChange?.(items.map((item) => item.id === file.id ? { ...item, title: newName } : item));
    // Update the item in the explorer if needed.
    refreshItemCache(file.id, { title: newName });
  };

  return (
    <FilePreview
      isOpen={!!currentItem}
      onClose={handleClosePreview}
      title={t("file_preview.title")}
      files={files}
      onChangeFile={handleChangePreviewItem}
      handleDownloadFile={() => handleDownloadItem(currentItem)}
      openedFileId={currentItem?.id}
      headerRightContent={
        <CustomFilesPreviewRightHeader currentItem={currentItem} />
      }
      sidebarContent={currentItem && <ItemInfo item={currentItem} />}
      onFileRename={handleFileRename}
    />
  );
};

type CustomFilesPreviewRightHeaderProps = {
  currentItem?: Item;
};

const CustomFilesPreviewRightHeader = ({
  currentItem,
}: CustomFilesPreviewRightHeaderProps) => {
  const { t } = useTranslation();
  const shareModal = useModal();

  if (!currentItem) {
    return null;
  }

  return (
    <>
      <div className="custom-files-preview-right-header">
        <Button variant="tertiary" onClick={shareModal.open}>
          {t("explorer.rightPanel.share")}
        </Button>
      </div>

      {shareModal.isOpen && (
        <ItemShareModal {...shareModal} item={currentItem} />
      )}
    </>
  );
};
