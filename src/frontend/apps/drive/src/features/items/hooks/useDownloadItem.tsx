import { Item, ItemUploadState } from "@/features/drivers/types";
import { ModalSize, useModals } from "@openfun/cunningham-react";
import { downloadFile } from "../utils";
import { useAuth } from "@/features/auth/Auth";
import { useTranslation } from "react-i18next";

export const useDownloadItem = () => {
  const { t } = useTranslation();
  const modals = useModals();
  const { user } = useAuth();
  const handleDownloadItem = async (item?: Item) => {
    if (!item?.url || !item?.title) {
      console.error("No url or title", item);
      return;
    }

    const itemState = item?.upload_state;
    const isCreator = item?.creator.id === user?.id;
    const isFileTooLarge =
      itemState === ItemUploadState.FILE_TOO_LARGE_TO_ANALYSE;
    const isSuspicious = itemState === ItemUploadState.SUSPICIOUS;
    const isPending =
      itemState === ItemUploadState.PENDING ||
      itemState === ItemUploadState.ANALYZING;

    let title: string | undefined;
    let description: string | undefined;

    if (isCreator && isSuspicious) {
      title = t("file_download_modal.suspicious.title");
      description = t("file_download_modal.description");
    } else if (!isCreator && (isFileTooLarge || isPending)) {
      title = isFileTooLarge
        ? t("file_download_modal.file_too_large.title")
        : t("file_download_modal.analyzing.title");
      description = t("file_download_modal.description");
    }

    if (title && description) {
      const decision = await modals.confirmationModal({
        size: ModalSize.MEDIUM,
        title,
        children: description,
      });

      if (decision === "yes") {
        // Only call downloadFile if both url and title are defined
        downloadFile(item.url, item.title);
      }
    } else {
      downloadFile(item.url, item.title);
    }
  };

  return { handleDownloadItem };
};
