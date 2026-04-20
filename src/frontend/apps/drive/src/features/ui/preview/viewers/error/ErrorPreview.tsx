import { useTranslation } from "react-i18next";

import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { FileIcon } from "@/features/explorer/components/icons/ItemIcon";
import { downloadFile } from "@/features/items/utils";
import { useCallback } from "react";
import { FilePreviewType } from "../../FilesPreview";
import { PreviewMessage } from "../../components/preview-message/PreviewMessage";

interface ErrorPreviewProps {
  file: FilePreviewType;
}

export const ErrorPreview = ({ file }: ErrorPreviewProps) => {
  const { t } = useTranslation();

  const handleDownload = useCallback(() => {
    downloadFile(file.url!, file.title);
  }, [file]);

  return (
    <PreviewMessage
      variant="error"
      icon={<FileIcon file={file} size="xlarge" />}
      title={t("file_preview.error.title")}
      description={t("file_preview.error.description")}
      action={
        <Button
          variant="bordered"
          icon={
            <Icon name="file_download" type={IconType.OUTLINED} size={16} />
          }
          onClick={handleDownload}
        >
          {t("file_preview.unsupported.download")}
        </Button>
      }
    />
  );
};
