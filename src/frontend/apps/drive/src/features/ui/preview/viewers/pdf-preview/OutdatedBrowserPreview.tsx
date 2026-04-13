import { useTranslation } from "react-i18next";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";

export const OutdatedBrowserPreview = () => {
  const { t } = useTranslation();

  return (
    <div className="file-preview-unsupported">
      <div className="file-preview-unsupported__icon">
        <Icon name="security" type={IconType.OUTLINED} size={48} />
      </div>
      <p className="file-preview-unsupported__title">
        {t("file_preview.outdated_browser.title")}
      </p>
      <p className="file-preview-unsupported__description">
        {t("file_preview.outdated_browser.description")}
      </p>
    </div>
  );
};
