import { useQuery } from "@tanstack/react-query";
import { getEntitlements } from "@/utils/entitlements";

export const useEntitlementsQuery = () => {
  return useQuery({
    queryKey: ["entitlements"],
    queryFn: getEntitlements,
    staleTime: 60_000,
  });
};

