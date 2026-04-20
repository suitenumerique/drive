import { useTranslation } from "react-i18next";

import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import mimeSuspicious from "@/assets/files/icons/suspicious_file.svg";
import { PreviewMessage } from "../../components/preview-message/PreviewMessage";

interface SuspiciousPreviewProps {
  handleDownload?: () => void;
}

export const SuspiciousPreview = ({
  handleDownload,
}: SuspiciousPreviewProps) => {
  const { t } = useTranslation();

  return (
    <PreviewMessage
      icon={
        <img src={mimeSuspicious.src} alt="" className="item-icon xlarge" />
      }
      title={t("file_preview.suspicious.title")}
      description={t("file_preview.suspicious.description")}
      action={
        handleDownload && (
          <Button
            variant="secondary"
            color="warning"
            icon={
              <Icon name="file_download" type={IconType.OUTLINED} size={16} />
            }
            onClick={handleDownload}
          >
            {t("file_preview.unsupported.download")}
          </Button>
        )
      }
    />
  );
};
