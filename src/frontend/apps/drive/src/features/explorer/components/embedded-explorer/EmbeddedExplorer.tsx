import clsx from "clsx";
import { Item } from "@/features/drivers/types";
import { useTranslation } from "react-i18next";
import { EmbeddedExplorerGridBreadcrumbs } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridBreadcrumbs";
import { useMemo, useState } from "react";
import { NavigationEvent } from "@/features/explorer/components/GlobalExplorerContext";
import { useQuery } from "@tanstack/react-query";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { ItemFilters } from "@/features/drivers/Driver";
import {
  EmbeddedExplorerGrid,
  EmbeddedExplorerGridProps,
} from "./EmbeddedExplorerGrid";
import { getRootItems } from "../../hooks/useQueries";
import { useAuth } from "@/features/auth/Auth";
import { useInfiniteChildren } from "../../hooks/useInfiniteChildren";
import { InfiniteScroll } from "@/features/ui/components/infinite-scroll/InfiniteScroll";

export type EmbeddedExplorerProps = {
  breadcrumbsRight?: () => React.ReactNode;
  emptyContent?: () => React.ReactNode;
  initialFolderId?: string;
  isCompact?: boolean;
  gridProps?: Partial<EmbeddedExplorerGridProps>;
  itemsFilter?: (items: Item[]) => Item[];
  currentItemId?: string | null;
  setCurrentItemId?: (itemId: string | null) => void;
  itemsFilters?: ItemFilters;
};

export const useEmbeddedExplorer = (props: EmbeddedExplorerProps) => {
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

/**
 * Standalone component to display the embedded explorer with:
 * - Breadcrumbs
 * - Grid
 * - Loader
 * - Empty state
 * - Compact mode
 * - Custom navigation
 * - Handles initial itemId or start directly from the workspaces
 *
 *
 * TODO:
 * - Add props custom navigation.
 */
export const EmbeddedExplorer = (props: EmbeddedExplorerProps) => {
  const { t } = useTranslation();
  const { user } = useAuth();

  // Update breadcrumbs when navigating
  const onNavigate = (event: NavigationEvent) => {
    const item = event.item as Item;
    props.gridProps?.setSelectedItems?.([]);
    props.setCurrentItemId?.(item?.id ?? null);
  };

  const { data: rootItems } = useQuery({
    queryKey: ["rootItems"],
    queryFn: getRootItems,
  });

  const infiniteChildrenQuery = useInfiniteChildren(
    props.currentItemId ?? null,
    props.itemsFilters ?? {}
  );

  // Extract children from infinite query pages
  const itemChildren = useMemo(() => {
    if (props.currentItemId === null) {
      return undefined;
    }
    // Return undefined if query is still loading, otherwise return the flattened array
    if (infiniteChildrenQuery.isLoading && !infiniteChildrenQuery.data) {
      return undefined;
    }
    return (
      infiniteChildrenQuery.data?.pages.flatMap((page) => page.children) ?? []
    );
  }, [
    infiniteChildrenQuery.data,
    infiniteChildrenQuery.isLoading,
    props.currentItemId,
  ]);

  const items = useMemo(() => {
    // If itemChildren are not loaded yet, we want to return undefined in order to display loading state.
    if (itemChildren === undefined && props.currentItemId) {
      return undefined;
    }
    let items = [];
    // If no itemId, we are in the root, we explorer spaces
    if (props.currentItemId === null) {
      if (user?.main_workspace) {
        items.push(user.main_workspace);
      }
      items = items.concat(rootItems ?? []);

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
  }, [
    props.currentItemId,
    rootItems,
    itemChildren,
    user?.main_workspace,
    props.itemsFilter,
    t,
  ]);

  const isEmpty = items?.length === 0;
  const isLoading = items === undefined;

  const getContent = () => {
    if (isLoading) {
      return <Spinner />;
    }
    if (isEmpty) {
      return (
        <>
          {props.emptyContent ? (
            props.emptyContent()
          ) : (
            <span className="embedded-explorer__empty">
              {t("explorer.grid.empty.default")}
            </span>
          )}
        </>
      );
    }

    const gridContent = (
      <EmbeddedExplorerGrid
        {...props.gridProps}
        isCompact={props.isCompact}
        items={items}
        onNavigate={onNavigate}
      />
    );

    // Add infinite scroll for folder children (not for root items)
    if (props.currentItemId !== null && infiniteChildrenQuery.hasNextPage) {
      return (
        <InfiniteScroll
          hasNextPage={infiniteChildrenQuery.hasNextPage}
          isFetchingNextPage={infiniteChildrenQuery.isFetchingNextPage}
          fetchNextPage={infiniteChildrenQuery.fetchNextPage}
        >
          {gridContent}
        </InfiniteScroll>
      );
    }

    return gridContent;
  };

  return (
    <div
      className={clsx("embedded-explorer", {
        "embedded-explorer--compact": props.isCompact,
      })}
    >
      <div className="embedded-explorer__container">
        <div className="embedded-explorer__breadcrumbs">
          <EmbeddedExplorerGridBreadcrumbs
            currentItemId={props.currentItemId ?? null}
            showSpacesItem={true}
            goToSpaces={() => {
              props.setCurrentItemId?.(null);
            }}
            onGoBack={(item) => {
              props.setCurrentItemId?.(item?.id ?? null);
            }}
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
