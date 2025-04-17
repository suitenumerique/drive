import { TreeItem } from "@/features/drivers/types";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { useRouter } from "next/router";

type ExplorerTreeNavItemProps = {
  icon: React.ReactNode;
  label: string;
  route: string;
};

export const ExplorerTreeNavItem = ({
  icon,
  label,
  route,
}: ExplorerTreeNavItemProps) => {
  const treeContext = useTreeContext<TreeItem>();
  const router = useRouter();
  const isActive = router.pathname === route;

  const handleClick = () => {
    router.push(route);
    treeContext?.treeData?.setSelectedNode(undefined);
  };

  return (
    <div
      className={`explorer__tree__nav__item ${isActive ? "active" : ""}`}
      onClick={handleClick}
    >
      <div className="explorer__tree__nav__item__icon">{icon}</div>
      <div className="explorer__tree__nav__item__label">{label}</div>
    </div>
  );
};
