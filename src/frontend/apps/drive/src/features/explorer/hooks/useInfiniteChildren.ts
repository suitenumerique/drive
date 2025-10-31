import { useInfiniteQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";

export const useInfiniteChildren = (
  itemId: string,
  filters: ItemFilters = {}
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
      return getDriver().getChildren(itemId, {
        page: pageParam.toString(),
        ...filters,
      });
    },
    getNextPageParam: (lastPage) => {
      return lastPage.pagination.hasMore
        ? lastPage.pagination.currentPage + 1
        : undefined;
    },
    initialPageParam: 1,
  });
};
