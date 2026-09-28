import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/Auth";
import { getDriver } from "@/features/config/Config";

export const useEntitlements = () => {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["entitlements"],
    queryFn: () => getDriver().getEntitlements(),
    enabled: !!user,
  });
};
