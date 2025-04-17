import { getDriver } from "@/features/config/Config";
import { UserFilters } from "@/features/drivers/Driver";
import { useQuery } from "@tanstack/react-query";
import { HookUseQueryOptions } from "@/utils/useQueries";
import { User } from "@/features/drivers/types";
export const useUsers = (
  filters?: UserFilters,
  options?: HookUseQueryOptions<User[]>
) => {
  const driver = getDriver();

  return useQuery({
    ...options,
    queryKey: ["users", filters],
    queryFn: () => driver.getUsers(filters),
  });
};
