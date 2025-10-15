import { useTranslation } from "react-i18next";

import { Button } from "@openfun/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import mimeSuspicious from "@/assets/files/icons/suspicious_file.svg";

interface SuspiciousPreviewProps {
  handleDownload?: () => void;
}

export const SuspiciousPreview = ({
  handleDownload,
}: SuspiciousPreviewProps) => {
  const { t } = useTranslation();

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

      {handleDownload && (
        <Button
          variant="secondary"
          color="warning"
          className="file-preview-suspicious__download-button"
          icon={
            <Icon name="file_download" type={IconType.OUTLINED} size={16} />
          }
          onClick={handleDownload}
        >
          {t("file_preview.unsupported.download")}
        </Button>
      )}
    </div>
  );
};
