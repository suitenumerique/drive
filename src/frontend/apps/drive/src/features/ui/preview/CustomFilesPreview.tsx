import { Item, ItemType } from "@/features/drivers/types";
import { FilePreview, FilePreviewType } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import posthog from "posthog-js";
import { itemToPreviewFile } from "@/features/explorer/utils/utils";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ItemInfo } from "@/features/items/components/ItemInfo";
import { Button, useModal } from "@gouvfr-lasuite/cunningham-react";
import { ItemShareModal } from "@/features/explorer/components/modals/share/ItemShareModal";
import { openWopiInNewTab } from "@/features/wopi/openWopi";

type CustomFilesPreviewProps = {
  currentItem?: Item;
  items: Item[];
  setPreviewItem?: (item?: Item) => void;
};

export const CustomFilesPreview = ({
  currentItem,
  items,
  setPreviewItem,
}: CustomFilesPreviewProps) => {
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

  return (
    <FilePreview
      isOpen={!!currentItem}
      onClose={handleClosePreview}
      files={files}
      onChangeFile={handleChangePreviewItem}
      handleDownloadFile={() => handleDownloadItem(currentItem)}
      openedFileId={currentItem?.id}
      onFileOpen={(file) =>
        posthog.capture("file_preview_opened", {
          id: file.id,
          size: file.size,
          mimetype: file.mimetype,
        })
      }
      onOpenInEditor={openWopiInNewTab}
      headerRightContent={
        <CustomFilesPreviewRightHeader currentItem={currentItem} />
      }
      sidebarContent={currentItem && <ItemInfo item={currentItem} />}
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
