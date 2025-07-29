import { useTranslation } from "react-i18next";
import { FilePreviewType } from "../files-preview/FilesPreview";

import { Button } from "@openfun/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { downloadFile } from "@/features/items/utils";
import { useCallback } from "react";
import mimeSuspicious from "@/assets/files/icons/suspicious_file.svg";

interface SuspiciousPreviewProps {
  file: FilePreviewType;
}

export const SuspiciousPreview = ({ file }: SuspiciousPreviewProps) => {
  const { t } = useTranslation();

  const handleDownload = useCallback(() => {
    downloadFile(file.url!, file.title);
  }, [file]);

  return (
    <div className="file-preview-suspicious">
      <div className="file-preview-suspicious__icon">
        <img src={mimeSuspicious.src} alt="" className="item-icon xlarge" />
      </div>
      <span className="file-preview-suspicious__title">
        {t("file_preview.suspicious.title")}
      </span>
      <span className="file-preview-suspicious__description">
        {t("file_preview.suspicious.description")}
      </span>

      <Button
        color="tertiary"
        className="file-preview-suspicious__download-button"
        icon={<Icon name="file_download" type={IconType.OUTLINED} size={16} />}
        onClick={handleDownload}
      >
        {t("file_preview.unsupported.download")}
      </Button>
    </div>
  );
};
