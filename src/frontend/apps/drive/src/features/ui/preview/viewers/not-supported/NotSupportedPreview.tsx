import { useTranslation } from "react-i18next";
import { FilePreviewType } from "../../FilesPreview";

import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { FileIcon } from "@/features/explorer/components/icons/ItemIcon";
import { useCallback } from "react";

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
    <div className="file-preview-unsupported">
      <div className="file-preview-unsupported__icon">
        <FileIcon file={file} size="xlarge" />
      </div>
      <p className="file-preview-unsupported__title">{file.title}</p>
      <p className="file-preview-unsupported__description">
        {title || (
          <>
            <strong>{t("file_preview.unsupported.disclaimer")}</strong>{" "}
            {t("file_preview.unsupported.description")}
          </>
        )}
      </p>

      {onDownload && (
        <Button
          variant="secondary"
          color="neutral"
          className="file-preview-unsupported__download-button"
          icon={
            <Icon name="file_download" type={IconType.OUTLINED} size={16} />
          }
          onClick={handleDownload}
        >
          {t("file_preview.suspicious.download")}
        </Button>
      )}
    </div>
  );
};
