import { getDriver } from "@/features/config/Config";
import { useQuery } from "@tanstack/react-query";

export const useBreadcrumbQuery = (id?: string | null) => {
  const driver = getDriver();
  return useQuery({
    queryKey: ["breadcrumb", id],
    queryFn: () => driver.getItemBreadcrumb(id!),
    enabled: !!id,
    placeholderData: (previousData) => previousData,
  });
};

/**
 * Fetches the item and its breadcrumb in a single atomic query, so the two
 * pieces never go out of sync during navigation. Combined with
 * `placeholderData: previousData`, the previous chain remains visible until
 * the new pair has resolved together — preventing the empty-middle flicker.
 */
export const useItemWithBreadcrumb = (id?: string | null) => {
  const driver = getDriver();
  return useQuery({
    queryKey: ["itemWithBreadcrumb", id],
    queryFn: async () => {
      const [item, breadcrumb] = await Promise.all([
        driver.getItem(id!),
        driver.getItemBreadcrumb(id!),
      ]);
      return { item, breadcrumb };
    },
    enabled: !!id,
    placeholderData: (previousData) => previousData,
  });
};
