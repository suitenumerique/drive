import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";
import { Item } from "@/features/drivers/types";
import { HookUseQueryOptions } from "@/utils/useQueries";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

export const useFavoriteItems = () => {
  return useQuery({
    queryKey: ["items", "favorites"],
    queryFn: () => getDriver().getFavoriteItems(),
  });
};

export const useItemAccesses = (itemId: string) => {
  return useQuery({
    queryKey: ["itemAccesses", itemId],
    queryFn: () => getDriver().getItemAccesses(itemId),
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

export const useFirstLevelItems = () => {
  return useQuery({
    queryKey: ["firstLevelItems"],
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    queryFn: () => getRootItems(),
  });
};

export const useItems = () => {
  return useQuery({
    queryKey: ["items"],
    queryFn: () => getRootItems(),
  });
};

export const getRootItems = async (filters?: ItemFilters) => {
  const result = await getDriver().getItems(filters);
  return result.children;
};

export const useItem = (
  itemId: string,
  options?: HookUseQueryOptions<Item>
) => {
  return useQuery({
    queryKey: ["items", itemId],
    queryFn: () => getDriver().getItem(itemId),
    ...options,
  });
};
