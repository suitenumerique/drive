import { useTranslation } from "react-i18next";
import { FilePreviewType } from "../files-preview/FilesPreview";

import { Button } from "@openfun/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { FileIcon } from "@/features/explorer/components/icons/ItemIcon";
import { downloadFile } from "@/features/items/utils";
import { useCallback } from "react";

interface ErrorPreviewProps {
  file: FilePreviewType;
}

export const ErrorPreview = ({ file }: ErrorPreviewProps) => {
  const { t } = useTranslation();

  const handleDownload = useCallback(() => {
    downloadFile(file.url!, file.title);
  }, [file]);

  return (
    <div className="file-preview-error">
      <div className="file-preview-error__icon">
        <FileIcon file={file} size="xlarge" />
      </div>
      <div className="file-preview-error__title">
        {t("file_preview.error.title")}
      </div>
      <div className="file-preview-error__description">
        {t("file_preview.error.description")}
      </div>

      <Button
        color="tertiary"
        className="file-preview-error__download-button"
        icon={<Icon name="file_download" type={IconType.OUTLINED} size={16} />}
        onClick={handleDownload}
      >
        {t("file_preview.unsupported.download")}
      </Button>
    </div>
  );
};
