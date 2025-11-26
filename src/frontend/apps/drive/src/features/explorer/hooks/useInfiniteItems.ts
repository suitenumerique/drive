import { useInfiniteQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";

export const useInfiniteItems = (
  filters: ItemFilters = {},
  enabled: boolean = true
) => {
  return useInfiniteQuery({
    queryKey: [
      "items",
      "infinite",
      ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
    ],
    queryFn: ({ pageParam = 1 }) => {
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
