import { UseQueryOptions } from "@tanstack/react-query";


export type HookUseQueryOptions2 = {
  enabled?: boolean;
}




export type HookUseQueryOptions<T> = Omit<UseQueryOptions<T>, "queryKey" | "queryFn">;

