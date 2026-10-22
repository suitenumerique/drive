import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";

/**
 * The live announcements published from the Django admin, sorted by priority.
 */
export const useAnnouncements = () => {
  return useQuery({
    queryKey: ["announcements"],
    queryFn: () => getDriver().getAnnouncements(),
    staleTime: 60 * 1000,
  });
};
