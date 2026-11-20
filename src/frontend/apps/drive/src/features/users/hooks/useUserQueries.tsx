import { getDriver } from "@/features/config/Config";
import { ContactFilters, UserFilters } from "@/features/drivers/Driver";
import { useQuery } from "@tanstack/react-query";
import { HookUseQueryOptions } from "@/utils/useQueries";
import { Contact, User, UserLight } from "@/features/drivers/types";
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

/**
 * People and groups to share with, as the share modal suggests them.
 */
export const useContactSearch = (
  filters?: ContactFilters,
  options?: HookUseQueryOptions<Contact[]>,
) => {
  const driver = getDriver();

  return useQuery({
    ...options,
    queryKey: ["contactSearch", filters],
    queryFn: () => driver.searchContacts(filters),
  });
};
