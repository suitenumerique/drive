import { useTranslation } from "react-i18next";
import { ExplorerTreeNavItem } from "./ExplorerTreeNavItem";
import { HorizontalSeparator, IconSize } from "@gouvfr-lasuite/ui-kit";
import { TrashIcon } from "@/features/ui/components/icon/TrashIcon";

export const ExplorerTreeNav = () => {
  const { t } = useTranslation();

  const navItems = [
    {
      icon: <TrashIcon size={IconSize.SMALL} />,
      label: t("explorer.tree.trash"),
      route: "/explorer/trash",
    },
  ];

  return (
    <div className="explorer__tree__nav__container">
      <HorizontalSeparator withPadding={false} />
      <div className="explorer__tree__nav">
        {navItems.map((item) => (
          <ExplorerTreeNavItem key={item.label} {...item} />
        ))}
      </div>
    </div>
  );
};
