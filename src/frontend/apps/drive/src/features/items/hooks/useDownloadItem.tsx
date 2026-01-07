import { Item, ItemUploadState } from "@/features/drivers/types";
import { ModalSize, useModals } from "@openfun/cunningham-react";
import { downloadFile } from "../utils";
import { useAuth } from "@/features/auth/Auth";
import { useTranslation } from "react-i18next";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import posthog from "posthog-js";

export const useDownloadItem = () => {
  const { t } = useTranslation();

  const modals = useModals();
  const { user } = useAuth();
  const handleDownloadItem = async (item?: Item) => {
    if (!item?.url || !item?.title) {
      addToast(
        <ToasterItem type="error">
          <span className="material-icons">error</span>
          <span>{t("file_download_modal.error.no_url_or_title")}</span>
        </ToasterItem>
      );
      return;
    }

    const itemState = item?.upload_state;
    const isCreator = item?.creator.id === user?.id;
    const isFileTooLarge =
      itemState === ItemUploadState.FILE_TOO_LARGE_TO_ANALYZE;
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


    const triggerDownload = () => {
      posthog.capture("file_download", {
        id: item.id,
        size: item.size,
        mimetype: item.mimetype,
      });
      downloadFile(item.url!, item.title);
    };

    if (title && description) {
      const decision = await modals.confirmationModal({
        size: ModalSize.MEDIUM,
        title,
        children: description,
      });

      if (decision === "yes") {
        // Only call downloadFile if both url and title are defined
        triggerDownload();
      }
    } else {
      triggerDownload();
    }
  };

  return { handleDownloadItem };
};
