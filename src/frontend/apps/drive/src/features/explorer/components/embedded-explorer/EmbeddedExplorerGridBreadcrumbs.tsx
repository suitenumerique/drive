import { useMemo, useState } from "react";
import { Item, ItemBreadcrumb } from "@/features/drivers/types";
import { getDefaultRoute } from "@/utils/defaultRoutes";
import {
  BreadcrumbItem,
  Breadcrumbs,
} from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { useTranslation } from "react-i18next";
import { Icon, IconSize } from "@gouvfr-lasuite/ui-kit";
import { NavigationItem } from "../GlobalExplorerContext";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import clsx from "clsx";
import { useBreadcrumbQuery } from "../../hooks/useBreadcrumb";
import { useItem } from "../../hooks/useQueries";
import { useRouter } from "next/router";
import { Button, useModal } from "@gouvfr-lasuite/cunningham-react";
import { ItemShareModal } from "../modals/share/ItemShareModal";

type BaseBreadcrumbsProps = {
  onGoBack?: (item: Item | ItemBreadcrumb) => void;
  goToSpaces?: () => void;
  currentItemId?: string | null;
  item?: Item;
  showAllFolderItem?: boolean;
  showMenuLastItem?: boolean;
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
  currentItemId,
  item: itemFromProps,
  forcedBreadcrumbsItems,
}: BaseBreadcrumbsProps) => {
  const { t, i18n } = useTranslation();
  const router = useRouter();

  const defaultRouteData = getDefaultRoute(router.pathname);
  const { data: breadcrumb } = useBreadcrumbQuery(currentItemId);

  const { data: fetchedItem } = useItem(currentItemId!, {
    enabled: !!currentItemId && !itemFromProps,
  });

  const item = itemFromProps ?? fetchedItem;

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

    if (defaultRouteData && !showSpacesItem) {
      breadcrumbsItems.push({
        content: (
          <div
            className="c__breadcrumbs__button"
            data-testid="default-route-button"
            role="button"
            tabIndex={0}
            onClick={() => {
              router.push(defaultRouteData.route);
            }}
          >
            <img
              src={defaultRouteData.breadcrumbIconSrc}
              alt={defaultRouteData.label}
              width={24}
              height={24}
            />

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
  }, [
    showSpacesItem,
    currentItemId,
    item,
    breadcrumb,
    forcedBreadcrumbsItems,
    i18n.language,
  ]);

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
  const shareModal = useModal();

  return (
    <div className="embedded-explorer__breadcrumbs__last-item">
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
      {item.nb_accesses && item.nb_accesses > 1 && (
        <>
          <Button
            variant="tertiary"
            size="small"
            icon={
              <Icon
                name="people"
                size={IconSize.SMALL}
                color="var(--c--contextuals--content--semantic--neutral--tertiary)"
              />
            }
            onClick={() => shareModal.open()}
          />
          {shareModal.isOpen && <ItemShareModal {...shareModal} item={item} />}
        </>
      )}
    </div>
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
