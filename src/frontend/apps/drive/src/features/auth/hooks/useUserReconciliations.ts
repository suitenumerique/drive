import { useQuery } from "@tanstack/react-query";

import { getDriver } from "@/features/config/Config";

export const KEY_USER_RECONCILIATION = "user-reconciliation";

export type UserReconciliationType = "active" | "inactive";

/**
 * Confirms a user reconciliation email by hitting the backend endpoint.
 *
 * The query is only enabled once a string confirmation id is available, and
 * opts out of the global error toast so the page can render its own error
 * state.
 */
export const useUserReconciliationQuery = (
  userType: UserReconciliationType,
  confirmationId?: string,
) => {
  const driver = getDriver();
  return useQuery({
    queryKey: [KEY_USER_RECONCILIATION, userType, confirmationId],
    queryFn: async () => {
      await driver.confirmUserReconciliation(userType, confirmationId!);
      return null;
    },
    enabled: typeof confirmationId === "string",
    meta: { noGlobalError: true },
    retry: false,
  });
};
