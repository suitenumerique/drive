import { useTranslation } from "react-i18next";
import { FilePreviewType } from "../../FilesPreview";

import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { FileIcon } from "@/features/explorer/components/icons/ItemIcon";
import { useCallback } from "react";
import { PreviewMessage } from "../../components/preview-message/PreviewMessage";

interface NotSupportedPreviewProps {
  file: FilePreviewType;
  onDownload?: (file: FilePreviewType) => void;
  title?: string;
}

export const NotSupportedPreview = ({
  file,
  onDownload,
  title,
}: NotSupportedPreviewProps) => {
  const { t } = useTranslation();

  const handleDownload = useCallback(() => {
    onDownload?.(file);
  }, [onDownload, file]);

  return (
    <PreviewMessage
      icon={<FileIcon file={file} size="xlarge" />}
      title={file.title}
      description={
        title ?? (
          <>
            <strong>{t("file_preview.unsupported.disclaimer")}</strong>{" "}
            {t("file_preview.unsupported.description")}
          </>
        )
      }
      action={
        onDownload && (
          <Button
            variant="secondary"
            color="neutral"
            icon={
              <Icon name="file_download" type={IconType.OUTLINED} size={16} />
            }
            onClick={handleDownload}
          >
            {t("file_preview.suspicious.download")}
          </Button>
        )
      }
    />
  );
};
