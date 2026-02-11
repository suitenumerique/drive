import type { ApiConfig } from "@/features/drivers/types";

let runtimeConfig: ApiConfig | undefined;

export const setRuntimeConfig = (config: ApiConfig) => {
  runtimeConfig = config;
};

export const getRuntimeConfig = (): ApiConfig | undefined => runtimeConfig;

