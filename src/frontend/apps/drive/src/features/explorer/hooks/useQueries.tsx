import { getDriver } from "@/features/config/Config";
import { useQuery } from "@tanstack/react-query";

export const useItemAccesses = (itemId: string) => {
  const driver = getDriver();

  const { data, isLoading, error } = useQuery({
    queryKey: ["itemAccesses", itemId],
    queryFn: () => driver.getItemAccesses(itemId),
  });

  return {
    data,
    isLoading,
    error,
  };
};

export const useItemInvitations = (itemId: string) => {
  const driver = getDriver();

  const { data, isLoading, error } = useQuery({
    queryKey: ["itemInvitations", itemId],
    queryFn: () => driver.getItemInvitations(itemId),
  });

  return {
    data,
    isLoading,
    error,
  };
};
