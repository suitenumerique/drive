import { useTranslation } from "react-i18next";
import { FilePreviewType } from "../files-preview/FilesPreview";

import { Button } from "@openfun/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { IconFromMimeType } from "@/features/explorer/components/icons/ItemIcon";

interface NotSupportedPreviewProps {
  file: FilePreviewType;
}

export const NotSupportedPreview = ({ file }: NotSupportedPreviewProps) => {
  const { t } = useTranslation();

  const handleDownload = async () => {
    // Temporary solution, waiting for a proper download_url attribute.
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = file.url!;
    a.download = file.title;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="file-preview-unsupported">
      <div className="file-preview-unsupported__icon">
        <IconFromMimeType mimeType={file.mimetype} size="xlarge" />
      </div>
      <p className="file-preview-unsupported__title">
        {t("file_preview.unsupported.title")}
      </p>
      <p className="file-preview-unsupported__description">
        {t("file_preview.unsupported.description")}
      </p>

      <Button
        color="tertiary"
        className="file-preview-unsupported__download-button"
        icon={<Icon name="file_download" type={IconType.OUTLINED} size={16} />}
        onClick={handleDownload}
      >
        {t("file_preview.unsupported.download")}
      </Button>
    </div>
  );
};
