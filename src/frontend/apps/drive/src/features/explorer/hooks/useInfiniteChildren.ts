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
    queryFn: ({ pageParam = 1 }) =>
      getDriver().getPaginatedChildren(itemId, pageParam, filters),
    getNextPageParam: (lastPage) =>
      lastPage.pagination.hasMore ? lastPage.pagination.nextPage : undefined,
    initialPageParam: 1,
  });
};
