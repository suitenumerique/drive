import { getDriver } from "@/features/config/Config";
import { UserFilters } from "@/features/drivers/Driver";
import { useQuery } from "@tanstack/react-query";
import { HookUseQueryOptions } from "@/utils/useQueries";
import { User, UserLight } from "@/features/drivers/types";
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

export const useContacts = (
  filters?: UserFilters,
  options?: HookUseQueryOptions<UserLight[]>
) => {
  const driver = getDriver();

  return useQuery({
    ...options,
    queryKey: ["contacts", filters],
    queryFn: () => driver.getContacts(filters),
  });
};
