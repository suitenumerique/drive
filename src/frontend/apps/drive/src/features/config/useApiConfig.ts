import { useQuery } from "@tanstack/react-query";
import { getDriver } from "./Config";

export function useApiConfig() {
  const driver = getDriver();
  return useQuery({
    queryKey: ["config"],
    queryFn: () => driver.getConfig(),
    staleTime: 1000,
  });
}
