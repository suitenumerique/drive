import { useTranslation } from "react-i18next";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { FileIcon } from "@/features/explorer/components/icons/ItemIcon";
import { FilePreviewType } from "../../FilesPreview";
import { openWopiInNewTab } from "./openWopi";

interface WopiOpenInEditorProps {
  file: FilePreviewType;
}

export const WopiOpenInEditor = ({ file }: WopiOpenInEditorProps) => {
  const { t } = useTranslation();

  return (
    <div className="file-preview-unsupported" data-preview-backdrop="true">
      <div className="file-preview-unsupported__icon">
        <FileIcon file={file} size="xlarge" />
      </div>
      <p className="file-preview-unsupported__title">{file.title}</p>
      <p className="file-preview-unsupported__description">
        {t("file_preview.wopi.open_in_editor_description")}
      </p>

      <Button
        className="file-preview-unsupported__download-button"
        icon={<Icon name="open_in_new" type={IconType.OUTLINED} size={16} />}
        onClick={() => openWopiInNewTab(file.id)}
      >
        {t("file_preview.wopi.open_in_editor")}
      </Button>
    </div>
  );
};
