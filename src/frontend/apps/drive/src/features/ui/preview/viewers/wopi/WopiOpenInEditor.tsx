import { useTranslation } from "react-i18next";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { FileIcon } from "@/features/explorer/components/icons/ItemIcon";
import { FilePreviewType } from "../../FilesPreview";
import { openWopiInNewTab } from "./openWopi";
import { PreviewMessage } from "../../components/preview-message/PreviewMessage";

interface WopiOpenInEditorProps {
  file: FilePreviewType;
}

export const WopiOpenInEditor = ({ file }: WopiOpenInEditorProps) => {
  const { t } = useTranslation();

  return (
    <PreviewMessage
      icon={<FileIcon file={file} size="xlarge" />}
      title={file.title}
      description={t("file_preview.wopi.open_in_editor_description")}
      action={
        <Button
          icon={<Icon name="open_in_new" type={IconType.OUTLINED} size={16} />}
          onClick={() => openWopiInNewTab(file.id)}
        >
          {t("file_preview.wopi.open_in_editor")}
        </Button>
      }
    />
  );
};
