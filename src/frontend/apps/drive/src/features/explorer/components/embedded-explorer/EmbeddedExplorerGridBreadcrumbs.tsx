import { useMemo, useState } from "react";
import { Item, ItemBreadcrumb, LinkReach } from "@/features/drivers/types";
import {
  DefaultRoute,
  DefaultRouteData,
  getDefaultRoute,
  ORDERED_DEFAULT_ROUTES,
} from "@/utils/defaultRoutes";
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
import { Button, Tooltip, useModal } from "@gouvfr-lasuite/cunningham-react";
import { ItemShareModal } from "../modals/share/ItemShareModal";
import {
  clearFromRoute,
  getFromRoute,
  getManualNavigationItemId,
} from "../../utils/utils";
import { useAuth } from "@/features/auth/Auth";

type BaseBreadcrumbsProps = {
  onGoBack?: (item: Item | ItemBreadcrumb) => void;
  goToSpaces?: () => void;
  currentItemId?: string | null;
  item?: Item;
  showAllFolderItem?: boolean;
  showMenuLastItem?: boolean;
  forcedBreadcrumbsItems?: ItemBreadcrumb[];
};

/**
 * ExplorerGridBreadcrumbs is a component that displays the breadcrumbs of the current item.
 * It can be used in controlled or uncontrolled.
 *
 * For the uncontrolled mode, if buildWithTreeContext is true, it will use the tree context to get the ancestors.
 */
export const EmbeddedExplorerGridBreadcrumbs = ({
  ...props
}: BaseBreadcrumbsProps) => {
  return <BaseBreadcrumbs {...props} />;
};

/**
 * BaseBreadcrumbs is a component that displays the breadcrumbs of the current item.
 * This is the base behavior for breadcrumbs.
 */
const BaseBreadcrumbs = ({
  onGoBack,
  goToSpaces,
  showAllFolderItem = false,
  showMenuLastItem = false,
  currentItemId,
  item: itemFromProps,
  forcedBreadcrumbsItems,
}: BaseBreadcrumbsProps) => {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const { user } = useAuth();

  const defaultRouteData = getDefaultRoute(router.pathname);
  const { data: breadcrumb } = useBreadcrumbQuery(currentItemId);

  const { data: fetchedItem } = useItem(currentItemId!, {
    enabled: !!currentItemId && !itemFromProps,
  });

  const item = itemFromProps ?? fetchedItem;

  const handleGoBack = (item: Item | ItemBreadcrumb) => {
    onGoBack?.(item);
  };

  const getDefaultRouteButton = (defaultRouteData: DefaultRouteData) => {
    return (
      <div
        className="c__breadcrumbs__button"
        data-testid="default-route-button"
        role="button"
        tabIndex={0}
        onClick={() => {
          router.push(defaultRouteData.route);
        }}
      >
        {defaultRouteData.icon({ size: IconSize.MEDIUM })}

        {t(defaultRouteData.label)}
      </div>
    );
  };

  /**
   * When passing through my-files, favorites, shared with me, etc. we set a fromRoute key in the session storage.
   * When the user navigates by clicking on folders, we set a manualNavigationItemId key in the session storage.
   * This is used to make sure to keep track of the fromRoute to display in the breadcrumbs.
   * This method returns the default route data to display in the breadcrumbs for manual navigation.
   */
  const getFromRouteManualDefaultRouteData = () => {
    if (!item) {
      return null;
    }
    const fromRoute = getFromRoute();
    if (!fromRoute) {
      return null;
    }
    const manualNavigationItemId = getManualNavigationItemId();
    if (!manualNavigationItemId) {
      return null;
    }

    // Use case: the user paste a new url ( from another user for instance ) in the browser.
    // On this new url we do not want to show the from route button because it will not
    // make any sense. So we check if the manual navigation item id is the same as the current item id.
    if (manualNavigationItemId !== item.id) {
      // Make sure to clear, otherwise, if the user click on another folder, the from route stored we will displayed, which
      // could be the wrong one.
      clearFromRoute();
      return null;
    }
    const defaultRouteData_ = ORDERED_DEFAULT_ROUTES.find(
      (r) => r.id === fromRoute,
    );
    if (!defaultRouteData_) {
      return null;
    }
    return defaultRouteData_;
  };

  /**
   * When the user is landing from a new url, we guess the default route to display in the breadcrumbs.
   * This is used to make sure to display the correct default route in the breadcrumbs.
   * This method returns the default route data to display in the breadcrumbs for guessed navigation.
   */
  const getGuessedDefaultRouteData = () => {
    if (!item) {
      return null;
    }
    // We either show the shared with me page or the my files page when user is
    // landing from a new url.
    let defaultRouteData_ = ORDERED_DEFAULT_ROUTES.find(
      (r) => r.id === DefaultRoute.SHARED_WITH_ME,
    )!;
    if (item.creator?.id === user?.id) {
      defaultRouteData_ = ORDERED_DEFAULT_ROUTES.find(
        (r) => r.id === DefaultRoute.MY_FILES,
      )!;
    }
    return defaultRouteData_;
  };

  /**
   * Rely on manual navigation if possible, otherwise guess the default route to display in the breadcrumbs.
   */
  const getFromRouteButton = () => {
    if (!item) {
      return null;
    }

    // Manual.
    const fromRouteManualDefaultRouteData =
      getFromRouteManualDefaultRouteData();
    if (fromRouteManualDefaultRouteData) {
      return getDefaultRouteButton(fromRouteManualDefaultRouteData);
    }

    // Guessed.
    const guessedDefaultRouteData = getGuessedDefaultRouteData();
    if (guessedDefaultRouteData) {
      return getDefaultRouteButton(guessedDefaultRouteData);
    }
    return null;
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

    if (defaultRouteData && !showAllFolderItem) {
      breadcrumbsItems.push({
        content: getDefaultRouteButton(defaultRouteData),
      });
    }

    const fromRouteButton = getFromRouteButton();
    if (fromRouteButton && !showAllFolderItem) {
      breadcrumbsItems.push({
        content: fromRouteButton,
      });
    }

    if (showAllFolderItem) {
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
    showAllFolderItem,
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
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const shareModal = useModal();
  const icon = useMemo(() => {
    if (item.computed_link_reach === LinkReach.PUBLIC) {
      return (
        <Icon
          name="public"
          size={IconSize.SMALL}
          color="var(--c--contextuals--content--semantic--neutral--tertiary)"
        />
      );
    }
    if (item.nb_accesses && item.nb_accesses > 1) {
      return (
        <Icon
          name="people"
          size={IconSize.SMALL}
          color="var(--c--contextuals--content--semantic--neutral--tertiary)"
        />
      );
    }

    return null;
  }, [item]);

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
      {item.is_encrypted && (
        <Tooltip
          content={t("explorer.breadcrumbs.encrypted", "Encrypted folder")}
        >
          <span
            className="material-icons"
            style={{
              fontSize: 18,
              color: "var(--c--theme--colors--success-600, #18753c)",
            }}
          >
            lock
          </span>
        </Tooltip>
      )}
      {icon && (
        <>
          <Button
            variant="tertiary"
            size="small"
            icon={icon}
            onClick={() => shareModal.open()}
            data-testid="share-button"
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
