import { useMemo, useState } from "react";
import { Item, ItemBreadcrumb } from "@/features/drivers/types";
import { DefaultRoute, ORDERED_DEFAULT_ROUTES } from "@/utils/defaultRoutes";
import {
  BreadcrumbItem,
  Breadcrumbs,
} from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { useTranslation } from "react-i18next";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { NavigationItem } from "../GlobalExplorerContext";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import clsx from "clsx";
import { useBreadcrumbQuery } from "../../hooks/useBreadcrumb";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { useRouter } from "next/router";

type BaseBreadcrumbsProps = {
  onGoBack?: (item: Item | ItemBreadcrumb) => void;
  goToSpaces?: () => void;
  currentItemId?: string | null;
  showAllFolderItem?: boolean;
  showMenuLastItem?: boolean;
  defaultRoute?: DefaultRoute;
  forcedBreadcrumbsItems?: ItemBreadcrumb[];
};

type GridBreadcrumbsProps = BaseBreadcrumbsProps & {
  showSpacesItem?: boolean;
};

/**
 * ExplorerGridBreadcrumbs is a component that displays the breadcrumbs of the current item.
 * It can be used in controlled or uncontrolled.
 *
 * For the uncontrolled mode, if buildWithTreeContext is true, it will use the tree context to get the ancestors.
 */
export const EmbeddedExplorerGridBreadcrumbs = ({
  ...props
}: GridBreadcrumbsProps) => {
  return <BaseBreadcrumbs {...props} />;
};

/**
 * BaseBreadcrumbs is a component that displays the breadcrumbs of the current item.
 * This is the base behavior for breadcrumbs.
 */
const BaseBreadcrumbs = ({
  onGoBack,
  goToSpaces,
  showAllFolderItem: showSpacesItem = false,
  showMenuLastItem = false,
  defaultRoute,
  currentItemId,
  forcedBreadcrumbsItems,
}: BaseBreadcrumbsProps) => {
  const { t } = useTranslation();
  const router = useRouter();
  const defaultRouteData = ORDERED_DEFAULT_ROUTES.find(
    (route) => route.id === defaultRoute
  );
  const { data: breadcrumb } = useBreadcrumbQuery(currentItemId);

  const { data: item } = useQuery({
    queryKey: ["item", currentItemId],
    queryFn: () => getDriver().getItem(currentItemId!),
    enabled: !!currentItemId,
  });

  const handleGoBack = (item: Item | ItemBreadcrumb) => {
    onGoBack?.(item);
  };

  const breadcrumbsItems = useMemo(() => {
    if (forcedBreadcrumbsItems) {
      return forcedBreadcrumbsItems.map((item) => ({
        content: (
          <BreadcrumbItemButton
            item={item}
            onClick={() => handleGoBack(item)}
          />
        ),
      }));
    }
    const breadcrumbsItems: BreadcrumbItem[] = [];

    if (defaultRouteData) {
      breadcrumbsItems.push({
        content: (
          <div
            className="c__breadcrumbs__button"
            onClick={() => {
              router.push(defaultRouteData.route);
            }}
          >
            <Icon name={defaultRouteData.iconName} />
            {t(defaultRouteData.label)}
          </div>
        ),
      });
    }

    if (showSpacesItem) {
      breadcrumbsItems.push({
        content: (
          <div
            className="c__breadcrumbs__button"
            onClick={() => {
              goToSpaces?.();
            }}
          >
            {t("explorer.breadcrumbs.all_folders")}
          </div>
        ),
      });
    }

    const breadcrumbsData = showMenuLastItem
      ? (breadcrumb ?? []).slice(0, -1)
      : (breadcrumb ?? []);

    const lastItem = item;

    breadcrumbsData.forEach((item) => {
      const isActive = item.id === lastItem?.id;
      breadcrumbsItems.push({
        content: (
          <BreadcrumbItemButton
            item={item}
            onClick={() => handleGoBack(item)}
            isActive={isActive}
          />
        ),
      });
    });

    if (showMenuLastItem && lastItem) {
      breadcrumbsItems.push({
        content: <LastItemBreadcrumb item={lastItem} />,
      });
    }

    return breadcrumbsItems;
  }, [showSpacesItem, currentItemId, item, breadcrumb, forcedBreadcrumbsItems]);

  return <Breadcrumbs items={breadcrumbsItems} />;
};

export type BreadcrumbItemProps = {
  item: ItemBreadcrumb | Item;
  isActive?: boolean;
  onClick: () => void;
  rightIcon?: React.ReactNode;
};
export const BreadcrumbItemButton = ({
  item,
  rightIcon,
  onClick,
  isActive = false,
}: BreadcrumbItemProps) => {
  return (
    <button
      className={clsx("c__breadcrumbs__button", {
        active: isActive,
      })}
      data-testid="breadcrumb-button"
      onClick={onClick}
    >
      {item.title}
      {rightIcon}
    </button>
  );
};

export const LastItemBreadcrumb = ({ item }: { item: Item }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <ItemActionDropdown
      item={item}
      isOpen={isOpen}
      setIsOpen={setIsOpen}
      trigger={
        <BreadcrumbItemButton
          isActive={true}
          item={item}
          onClick={() => setIsOpen(true)}
          rightIcon={<span className="material-icons">arrow_drop_down</span>}
        />
      }
    />
  );
};

/**
 * useBreadcrumbs is a hook that manages the breadcrumbs state.
 * It is used in the controlled mode.
 */
export const useBreadcrumbs = ({
  handleNavigate: handleNavigateFromProps,
}: {
  handleNavigate: (item?: NavigationItem) => void;
}) => {
  const [, setAncestors] = useState<NavigationItem[]>([]);

  const onGoBack = (item: ItemBreadcrumb) => {
    setAncestors((prev) => prev.slice(0, prev.indexOf(item) + 1));
    handleNavigateFromProps(item);
  };

  const resetAncestors = (items: ItemBreadcrumb[] = []) => {
    if (items?.length === 0) {
      setAncestors([]);
      handleNavigateFromProps(undefined);
    } else {
      setAncestors(items);
      handleNavigateFromProps(items[items.length - 1]);
    }
  };

  const goToSpaces = () => {
    resetAncestors();
    handleNavigateFromProps(undefined);
  };

  return {
    onGoBack,
    goToSpaces,
  };
};
