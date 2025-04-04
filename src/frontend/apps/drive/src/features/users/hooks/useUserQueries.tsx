import { getDriver } from "@/features/config/Config";
import { UserFilters } from "@/features/drivers/Driver";
import { useQuery } from "@tanstack/react-query";
import { HookUseQueryOptions } from "@/utils/useQueries";
export const useUsers = (
  filters?: UserFilters,
  options?: HookUseQueryOptions
) => {
  const driver = getDriver();

  return useQuery({
    ...options,
    queryKey: ["users", filters],
    queryFn: () => driver.getUsers(filters),
  });
};
