import { useInfiniteQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";

export const useInfiniteItems = (
  filters: ItemFilters = {},
  queryKey: string[] = ["items", "infinite"],
  enabled: boolean = true
) => {
  const effectiveQueryKey = [
    ...queryKey,
    ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
  ];
  return useInfiniteQuery({
    queryKey: effectiveQueryKey,
    queryFn: ({ pageParam = 1 }) => {
      if (filters.is_favorite) {
        return getDriver().getFavoriteItems({
          page: pageParam,
          ...filters,
        });
      }
      return getDriver().getItems({
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

export const useInfiniteRecentItems = (
  filters: ItemFilters = {},
  queryKey: string[] = ["items", "recent", "infinite"],
  enabled: boolean = true
) => {
  const effectiveQueryKey = [
    ...queryKey,
    ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
  ];
  return useInfiniteQuery({
    queryKey: effectiveQueryKey,
    queryFn: ({ pageParam = 1 }) => {
      return getDriver().getRecentItems({
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
