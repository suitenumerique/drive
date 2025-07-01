import clsx from "clsx";
import { ExplorerGridItems, ExplorerGridItemsProps } from "./ExplorerGridItems";
import { Item, ItemType } from "@/features/drivers/types";
import { useTranslation } from "react-i18next";
import {
  ExplorerGridBreadcrumbs,
  useBreadcrumbs,
} from "../breadcrumbs/ExplorerGridBreadcrumbs";
import { useEffect, useMemo, useState } from "react";
import { NavigationEvent } from "../ExplorerContext";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { Spinner, useTreeContext } from "@gouvfr-lasuite/ui-kit";

export type ExplorerGridItemsExplorerProps = {
  breadcrumbsRight?: () => React.ReactNode;
  emptyContent?: () => React.ReactNode;
  initialFolderId?: string;
  isCompact?: boolean;
  gridProps?: Partial<ExplorerGridItemsProps>;
  itemsFilter?: (items: Item[]) => Item[];
  currentItemId?: string | null;
  setCurrentItemId?: (itemId: string | null) => void;
};

export const useExplorerGridItemsExplorer = (
  props: ExplorerGridItemsExplorerProps
) => {
  const [selectedItems, setSelectedItems] = useState<Item[]>([]);
  const [currentItemId, setCurrentItemId] = useState<string | null>(
    props.initialFolderId ?? null
  );

  return {
    selectedItems,
    setSelectedItems,
    currentItemId,
    setCurrentItemId,
    ...props,
    gridProps: {
      ...props.gridProps,
      selectedItems,
      setSelectedItems,
    },
  };
};

export const ExplorerGridItemsExplorer = (
  props: ExplorerGridItemsExplorerProps
) => {
  const { t } = useTranslation();

  // TODO: Should not use tree.
  const treeContext = useTreeContext<Item>();

  const breadcrumbs = useBreadcrumbs({
    handleNavigate: (item) => {
      props.setCurrentItemId?.(item?.id ?? null);
    },
  });

  // Update breadcrumbs when navigating
  const onNavigate = (event: NavigationEvent) => {
    const item = event.item as Item;
    // setSelectedItems([]);
    breadcrumbs.update(item);
    props.setCurrentItemId?.(item?.id ?? null);
  };

  const { data: rootItems } = useQuery({
    queryKey: ["rootItems"],
    queryFn: () => getDriver().getItems(),
  });

  const { data: itemChildren } = useQuery({
    queryKey: ["items", props.currentItemId, "children", []],
    enabled: props.currentItemId !== null,
    queryFn: () => {
      if (props.currentItemId === null) {
        return Promise.resolve(undefined);
      }
      // TODO: Customize
      return getDriver().getChildren(props.currentItemId!, {
        type: ItemType.FOLDER,
      });
    },
  });

  const items = useMemo(() => {
    // If itemChildren are not loaded yet, we want to return undefined in order to display loading state.
    if (itemChildren === undefined && props.currentItemId) {
      return undefined;
    }
    let items = [];
    // If no itemId, we are in the root, we explorer spaces
    if (props.currentItemId === null) {
      items = rootItems ?? [];
      // Sort items to put main_workspace first
      items = items.sort((a, b) => {
        if (a.main_workspace && !b.main_workspace) return -1;
        if (!a.main_workspace && b.main_workspace) return 1;
        return 0;
      });
    } else {
      items = itemChildren ?? [];
    }

    if (props.itemsFilter) {
      items = props.itemsFilter(items);
    }

    items = items.map((item) => {
      if (item.main_workspace) {
        return {
          ...item,
          title: t("explorer.workspaces.mainWorkspace"),
        };
      }
      return item;
    });

    return items;
  }, [props.currentItemId, rootItems, itemChildren]);

  // set the breadcrumbs to the initial folder
  useEffect(() => {
    if (props.initialFolderId) {
      // TODO: Should not use tree.
      const history =
        (treeContext?.treeData.getAncestors(props.initialFolderId) as Item[]) ??
        [];
      breadcrumbs.resetAncestors(history);
    }
  }, [props.initialFolderId]);

  const isEmpty = items?.length === 0;
  const isLoading = items === undefined;

  const getContent = () => {
    if (isLoading) {
      return <Spinner />;
    }
    if (isEmpty) {
      return <>{props.emptyContent ? props.emptyContent() : "empty"}</>;
    }
    return (
      <ExplorerGridItems
        {...props.gridProps}
        isCompact={props.isCompact}
        items={items}
        onNavigate={onNavigate}
      />
    );
  };

  return (
    <div
      className={clsx("explorer__grid__items__explorer", {
        "explorer__grid__items__explorer--compact": props.isCompact,
      })}
    >
      <div className="explorer__grid__items__explorer__container">
        <div className="explorer__grid__items__explorer__breadcrumbs">
          <ExplorerGridBreadcrumbs
            {...breadcrumbs}
            showSpacesItem={true}
            buildWithTreeContext={false}
          />
          {props.breadcrumbsRight?.()}
        </div>
        <div
          className={clsx("c__datagrid explorer__grid", {
            "c__datagrid--empty": isEmpty,
            "c__datagrid--loading": isLoading,
          })}
        >
          {getContent()}
        </div>
      </div>
    </div>
  );
};
