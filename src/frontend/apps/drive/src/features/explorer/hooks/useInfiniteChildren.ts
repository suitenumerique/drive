import { useInfiniteQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";

export const useInfiniteChildren = (
  itemId: string | null,
  filters: ItemFilters = {},
  enabled: boolean = true
) => {
  return useInfiniteQuery({
    queryKey: [
      "items",
      itemId,
      "children",
      "infinite",
      ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
    ],
    queryFn: ({ pageParam = 1 }) => {
      if (!itemId) {
        throw new Error("itemId is required");
      }
      return getDriver().getChildren(itemId, {
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
    enabled: enabled && itemId !== null,
  });
};
