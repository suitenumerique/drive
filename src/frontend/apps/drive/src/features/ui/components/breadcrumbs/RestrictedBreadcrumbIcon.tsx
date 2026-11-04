import { IconSize } from "@gouvfr-lasuite/ui-components";
import { FolderRestricted } from "@gouvfr-lasuite/ui-components/icons";
import { useTranslation } from "react-i18next";
import { ItemBreadcrumb } from "@/features/drivers/types";

// Marks a restricted folder in a breadcrumb, labelled for screen readers.
export const RestrictedBreadcrumbIcon = ({
  item,
}: {
  item: Pick<ItemBreadcrumb, "is_restricted">;
}) => {
  const { t } = useTranslation();
  if (!item.is_restricted) {
    return null;
  }
  return (
    <FolderRestricted
      size={IconSize.SMALL}
      className="c__breadcrumbs__restricted"
      role="img"
      aria-label={t("explorer.breadcrumbs.restricted")}
    />
  );
};
