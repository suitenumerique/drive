import { getDriver } from "@/features/config/Config";
import { useQuery } from "@tanstack/react-query";

export const useBreadcrumbQuery = (id?: string | null) => {
  const driver = getDriver();
  return useQuery({
    queryKey: ["breadcrumb", id],
    queryFn: () => driver.getItemBreadcrumb(id!),
    enabled: !!id,
  });
};
