import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";
import { Item } from "@/features/drivers/types";
import { HookUseQueryOptions } from "@/utils/useQueries";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

export const useInfiniteItemAccesses = (itemId: string) => {
  const driver = getDriver();
  return useInfiniteQuery({
    queryKey: ["itemAccesses", itemId],
    queryFn: () => driver.getItemAccesses(itemId),
    initialPageParam: 1,
    getNextPageParam(lastPage, allPages) {
      return lastPage.next ? allPages.length + 1 : undefined;
    },
  });
};

export const useItems = (
  filters?: ItemFilters,
  options?: HookUseQueryOptions<Item[]>
) => {
  const driver = getDriver();
  return useQuery({
    queryKey: ["items", filters],
    queryFn: () => driver.getItems(filters),
    ...options,
  });
};

export const useInfiniteItemInvitations = (itemId: string) => {
  const driver = getDriver();
  return useInfiniteQuery({
    queryKey: ["itemInvitations", itemId],
    queryFn: () => driver.getItemInvitations(itemId),
    initialPageParam: 1,
    getNextPageParam(lastPage, allPages) {
      return lastPage.next ? allPages.length + 1 : undefined;
    },
  });
};
