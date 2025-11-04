import { useMemo, useState } from "react";
import { Item, ItemBreadcrumb } from "@/features/drivers/types";
import {
  BreadcrumbItem,
  Breadcrumbs,
} from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { useTranslation } from "react-i18next";
import { IconSize } from "@gouvfr-lasuite/ui-kit";
import { WorkspaceIcon } from "../icons/ItemIcon";
import { NavigationItem } from "../GlobalExplorerContext";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import clsx from "clsx";
import { useAuth } from "@/features/auth/Auth";
import { useBreadcrumbQuery } from "../../hooks/useBreadcrumb";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";

type BaseBreadcrumbsProps = {
  onGoBack?: (item: Item | ItemBreadcrumb) => void;
  goToSpaces?: () => void;
  currentItemId: string | null;
  showSpacesItem?: boolean;
  showMenuLastItem?: boolean;
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
  showSpacesItem = false,
  showMenuLastItem = false,

  currentItemId,
}: BaseBreadcrumbsProps) => {
  const { t } = useTranslation();

  const { data: breadcrumb } = useBreadcrumbQuery(currentItemId);

  const { data: item } = useQuery({
    queryKey: ["item", currentItemId],
    queryFn: () => getDriver().getItem(currentItemId!),
    enabled: currentItemId !== null,
  });

  const handleGoBack = (item: Item | ItemBreadcrumb) => {
    onGoBack?.(item);
  };

  const breadcrumbsItems = useMemo(() => {
    const breadcrumbsItems: BreadcrumbItem[] = [];
    if (showSpacesItem) {
      breadcrumbsItems.push({
        content: (
          <div
            className="c__breadcrumbs__button"
            onClick={() => {
              goToSpaces?.();
            }}
          >
            {t("explorer.breadcrumbs.spaces")}
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
  }, [showSpacesItem, currentItemId, item, breadcrumb]);

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
  const { user } = useAuth();
  const isMainWorkspace = item.id === user?.main_workspace?.id;
  const isWorkspace = item.path.split(".").length === 1;

  const { t } = useTranslation();
  return (
    <button
      className={clsx("c__breadcrumbs__button", {
        active: isActive,
      })}
      data-testid="breadcrumb-button"
      onClick={onClick}
    >
      {isWorkspace && (
        <WorkspaceIcon
          isMainWorkspace={isMainWorkspace}
          iconSize={IconSize.SMALL}
        />
      )}
      {isMainWorkspace ? t("explorer.workspaces.mainWorkspace") : item.title}
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
