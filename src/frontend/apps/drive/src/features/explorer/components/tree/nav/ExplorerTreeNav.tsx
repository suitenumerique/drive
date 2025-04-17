import { useTranslation } from "react-i18next";
import trashIcon from "@/assets/icons/trash.svg";
import { ExplorerTreeNavItem } from "./ExplorerTreeNavItem";
import { HorizontalSeparator } from "@gouvfr-lasuite/ui-kit";

export const ExplorerTreeNav = () => {
  const { t } = useTranslation();

  const navItems = [
    {
      icon: <img src={trashIcon.src} alt="" />,
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
