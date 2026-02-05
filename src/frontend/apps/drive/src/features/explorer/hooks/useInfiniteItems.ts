import { useInfiniteQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { ItemFilters, PaginatedChildrenResult } from "@/features/drivers/Driver";

type Fetcher = (filters: ItemFilters) => Promise<PaginatedChildrenResult>;

const createInfiniteItemsHook = (
  defaultQueryKey: string[],
  fetcher: Fetcher
) => {
  return (
    filters: ItemFilters = {},
    queryKey: string[] = defaultQueryKey,
    enabled: boolean = true
  ) => {
    const effectiveQueryKey = [
      ...queryKey,
      ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
    ];
    return useInfiniteQuery({
      queryKey: effectiveQueryKey,
      queryFn: ({ pageParam = 1 }) => {
        return fetcher({
          page: pageParam,
          ...filters,
        });
      },
      getNextPageParam: (lastPage) => {
        return lastPage.pagination.hasMore
          ? lastPage.pagination.currentPage + 1
          : undefined;
      },
      initialPageParam: 1,
      enabled: enabled,
    });
  };
};

export const useInfiniteItems = (
  filters: ItemFilters = {},
  queryKey: string[] = ["items", "infinite"],
  enabled: boolean = true
) => {
  const fetcher: Fetcher = filters.is_favorite
    ? (f) => getDriver().getFavoriteItems(f)
    : (f) => getDriver().getItems(f);

  return createInfiniteItemsHook(
    ["items", "infinite"],
    fetcher
  )(filters, queryKey, enabled);
};

export const useInfiniteRecentItems = createInfiniteItemsHook(
  ["items", "recent", "infinite"],
  (filters) => getDriver().getRecentItems(filters)
);
