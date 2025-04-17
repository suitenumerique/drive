import { getDriver } from "@/features/config/Config";
import { useInfiniteQuery } from "@tanstack/react-query";

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
