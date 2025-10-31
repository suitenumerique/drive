import { getDriver } from "@/features/config/Config";
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

export const getRootItems = async () => {
  const result = await getDriver().getItems();
  return result.children;
};
