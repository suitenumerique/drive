import clsx from "clsx";
import { Item, ItemBreadcrumb } from "@/features/drivers/types";
import { useTranslation } from "react-i18next";
import { EmbeddedExplorerGridBreadcrumbs } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridBreadcrumbs";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  NavigationEvent,
  getOriginalIdFromTreeId,
} from "@/features/explorer/components/GlobalExplorerContext";
import { useQuery } from "@tanstack/react-query";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { ItemFilters } from "@/features/drivers/Driver";
import {
  EmbeddedExplorerGrid,
  EmbeddedExplorerGridProps,
} from "./EmbeddedExplorerGrid";
import { useAuth } from "@/features/auth/Auth";
import { useInfiniteChildren } from "../../hooks/useInfiniteChildren";
import { InfiniteScroll } from "@/features/ui/components/infinite-scroll/InfiniteScroll";
import { getDriver } from "@/features/config/Config";
import { EmbeddedExplorerSearchInput } from "./EmbeddedExplorerSearchInput";
import { useInfiniteRecentItems } from "../../hooks/useInfiniteItems";

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
  showSearch?: boolean;
};

export const useEmbeddedExplorer = (props: EmbeddedExplorerProps) => {
  const [selectedItems, setSelectedItems] = useState<Item[]>([]);
  const [currentItemId, setCurrentItemId] = useState<string | null>(
    props.initialFolderId ?? null,
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
  const itemsRef = useRef<Item[]>([]);

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [inputSearchValue, setInputSearchValue] = useState<string>("");
  const timeoutRef = useRef<NodeJS.Timeout>(null);

  // Update breadcrumbs when navigating
  const onNavigate = (event: NavigationEvent) => {
    let item = event.item as Item;
    // Extract the original item ID from the tree ID (handles favorites path format)
    if (item.id.includes("::")) {
      item = { ...item, id: getOriginalIdFromTreeId(item.id) };
    }
    props.gridProps?.setSelectedItems?.([]);
    props.setCurrentItemId?.(item?.id ?? null);
    setInputSearchValue("");
    setSearchQuery("");
  };

  const rootItemsQuery = useInfiniteRecentItems(props.itemsFilters, [" "]);

  const { data: searchItems, isLoading: isSearchItemsLoading } = useQuery({
    queryKey: ["searchItems", searchQuery],
    queryFn: () =>
      getDriver().searchItems({
        title: searchQuery,
        ...props.itemsFilters,
      }),
    enabled: searchQuery !== "",
  });

  const infiniteChildrenQuery = useInfiniteChildren(
    props.currentItemId ?? null,
    props.itemsFilters ?? {},
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

  const rootItems = useMemo(() => {
    return rootItemsQuery?.data?.pages.flatMap((page) => page.children) ?? [];
  }, [rootItemsQuery.data]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const items = useMemo(() => {
    // If itemChildren are not loaded yet, we want to return undefined in order to display loading state.
    if (itemChildren === undefined && props.currentItemId) {
      return undefined;
    }
    if (isSearchItemsLoading) {
      return itemsRef.current;
    }
    let items: Item[] = [];

    if (searchQuery !== "") {
      items = searchItems ?? [];
    } else if (props.currentItemId === null) {
      items = items.concat(rootItems ?? []);
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

    itemsRef.current = items;
    return items;
  }, [
    props.currentItemId,
    rootItems,
    itemChildren,
    user?.main_workspace,
    props.itemsFilter,
    searchItems,
    searchQuery,
    isSearchItemsLoading,
    t,
  ]);

  const isEmpty = items?.length === 0;
  const isLoading = items === undefined;

  const handleSearch = (query: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setInputSearchValue(query);
    if (query === "") {
      setSearchQuery("");
      return;
    }
    timeoutRef.current = setTimeout(() => {
      setSearchQuery(query);
    }, 300);
  };

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

    const hasNextPage =
      infiniteChildrenQuery.hasNextPage || rootItemsQuery.hasNextPage;
    const isFetchingNextPage =
      infiniteChildrenQuery.isFetchingNextPage ||
      rootItemsQuery.isFetchingNextPage;
    const fetchNextPage = props.currentItemId
      ? infiniteChildrenQuery.fetchNextPage
      : rootItemsQuery.fetchNextPage;

    // Add infinite scroll for folder children (not for root items)
    if (hasNextPage) {
      return (
        <InfiniteScroll
          hasNextPage={hasNextPage}
          isFetchingNextPage={isFetchingNextPage}
          fetchNextPage={fetchNextPage}
        >
          {gridContent}
        </InfiniteScroll>
      );
    }

    return gridContent;
  };

  const forcedBreadcrumbsItems: ItemBreadcrumb[] | undefined = useMemo(() => {
    if (searchQuery !== "") {
      return [
        {
          id: "search",
          title: t("explorer.search.results_title", "Search results"),
          path: "",
          depth: 0,
          main_workspace: false,
        },
      ];
    }
    return undefined;
  }, [searchQuery, searchItems, t]);

  return (
    <>
      <div
        className={clsx("embedded-explorer", {
          "embedded-explorer--compact": props.isCompact,
          "embedded-explorer--with-search": props.showSearch,
        })}
      >
        {props.showSearch && (
          <EmbeddedExplorerSearchInput
            onSearch={handleSearch}
            value={inputSearchValue}
          />
        )}
        <div className="embedded-explorer__container">
          <div className="embedded-explorer__breadcrumbs">
            <EmbeddedExplorerGridBreadcrumbs
              currentItemId={props.currentItemId ?? null}
              forcedBreadcrumbsItems={forcedBreadcrumbsItems}
              showAllFolderItem={true}
              goToSpaces={() => {
                props.setCurrentItemId?.(null);
              }}
              onGoBack={(item) => {
                let currentItemId: string | null = item?.id ?? null;
                if (item.id === "search") {
                  currentItemId = null;
                }
                props.setCurrentItemId?.(currentItemId);
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
    </>
  );
};
