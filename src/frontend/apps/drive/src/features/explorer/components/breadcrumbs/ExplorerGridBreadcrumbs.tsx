import { useMemo, useState } from "react";
import { Item } from "@/features/drivers/types";
import {
  BreadcrumbItem,
  Breadcrumbs,
} from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { useTranslation } from "react-i18next";
import { IconSize, useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { ItemIcon } from "../icons/ItemIcon";

type BaseBreadcrumbsProps = {
  ancestors?: Item[];
  resetAncestors?: (items?: Item[]) => void;
  onGoBack?: (item: Item) => void;
  goToSpaces?: () => void;
  currentItemId?: string | null;
  showSpacesItem?: boolean;
};

type GridBreadcrumbsProps = BaseBreadcrumbsProps & {
  showSpacesItem?: boolean;
  buildWithTreeContext?: boolean;
};

type GridBreadcrumbsFromTreeProps = Omit<
  GridBreadcrumbsProps,
  "buildWithTreeContext" | "resetAncestors" | "ancestors"
> & {};

/**
 * ExplorerGridBreadcrumbs is a component that displays the breadcrumbs of the current item.
 * It can be used in controlled or uncontrolled.
 *
 * For the uncontrolled mode, if buildWithTreeContext is true, it will use the tree context to get the ancestors.
 */
export const ExplorerGridBreadcrumbs = ({
  buildWithTreeContext = false,
  ...props
}: GridBreadcrumbsProps) => {
  if (buildWithTreeContext) {
    return <GridBreadcrumbsFromTree {...props} />;
  }
  return <BaseBreadcrumbs {...props} />;
};

/**
 * GridBreadcrumbsFromTree is a component that displays the breadcrumbs of the current item.
 * It uses the tree context to get the ancestors.
 */
const GridBreadcrumbsFromTree = ({
  currentItemId,
  ...props
}: GridBreadcrumbsFromTreeProps) => {
  const treeContext = useTreeContext<Item>();
  const ancestors = currentItemId
    ? (treeContext?.treeData.getAncestors(currentItemId) as Item[])
    : [];
  return <BaseBreadcrumbs {...props} ancestors={ancestors} />;
};

/**
 * BaseBreadcrumbs is a component that displays the breadcrumbs of the current item.
 * This is the base behavior for breadcrumbs.
 */
const BaseBreadcrumbs = ({
  onGoBack,
  goToSpaces,
  showSpacesItem = false,

  ancestors,
  currentItemId,
  resetAncestors,
}: BaseBreadcrumbsProps) => {
  const { t } = useTranslation();

  const handleGoBack = (item: Item) => {
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
              resetAncestors?.([]);
            }}
          >
            {t("explorer.breadcrumbs.spaces")}
          </div>
        ),
      });
    }

    const breadcrumbsData = ancestors ?? [];

    breadcrumbsData.forEach((item) => {
      const isWorkspace = itemIsWorkspace(item) || item.main_workspace;

      breadcrumbsItems.push({
        content: (
          <button
            className="c__breadcrumbs__button"
            onClick={() => handleGoBack(item)}
          >
            {isWorkspace && <ItemIcon item={item} size={IconSize.SMALL} />}
            {item.main_workspace
              ? t("explorer.workspaces.mainWorkspace")
              : item.title}
          </button>
        ),
      });
    });

    return breadcrumbsItems;
  }, [ancestors, showSpacesItem, currentItemId]);

  return <Breadcrumbs items={breadcrumbsItems} />;
};

/**
 * useBreadcrumbs is a hook that manages the breadcrumbs state.
 * It is used in the controlled mode.
 */
export const useBreadcrumbs = ({
  handleNavigate: handleNavigateFromProps,
}: {
  handleNavigate: (item?: Item) => void;
}) => {
  const [ancestors, setAncestors] = useState<Item[]>([]);

  const update = (item: Item) => {
    setAncestors((prev) => {
      return [...prev, item];
    });
    // handleNavigateFromProps(item);
  };

  const onGoBack = (item: Item) => {
    setAncestors((prev) => prev.slice(0, prev.indexOf(item) + 1));
    handleNavigateFromProps(item);
  };

  const resetAncestors = (items: Item[] = []) => {
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
    // Methods to be used by the parent.
    update,
    resetAncestors,
    // Props to be passed to the component.
    ancestors,
    onGoBack,
    goToSpaces,
  };
};
