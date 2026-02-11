import type { ApiConfig } from "@/features/drivers/types";

export type TimeBound = { still_working_ms: number; fail_ms: number };

export type OperationTimeBounds = Record<string, TimeBound>;

export const DEFAULT_OPERATION_TIME_BOUNDS_MS: OperationTimeBounds = {
  config_load: { still_working_ms: 3000, fail_ms: 15000 },
  wopi_info: { still_working_ms: 5000, fail_ms: 20000 },
  wopi_iframe: { still_working_ms: 5000, fail_ms: 60000 },
  preview_pdf: { still_working_ms: 3000, fail_ms: 15000 },
  upload_create: { still_working_ms: 5000, fail_ms: 20000 },
  upload_put: { still_working_ms: 10000, fail_ms: 900000 },
  upload_finalize: { still_working_ms: 5000, fail_ms: 60000 },
};

const isTimeBound = (value: unknown): value is TimeBound => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const v = value as Record<string, unknown>;
  return (
    typeof v.still_working_ms === "number" &&
    Number.isFinite(v.still_working_ms) &&
    v.still_working_ms >= 0 &&
    typeof v.fail_ms === "number" &&
    Number.isFinite(v.fail_ms) &&
    v.fail_ms >= 0
  );
};

export const resolveOperationTimeBounds = (
  config?: ApiConfig
): OperationTimeBounds => {
  const overrides = config?.FRONTEND_OPERATION_TIME_BOUNDS_MS;
  if (!overrides || typeof overrides !== "object") {
    return DEFAULT_OPERATION_TIME_BOUNDS_MS;
  }

  const merged: OperationTimeBounds = { ...DEFAULT_OPERATION_TIME_BOUNDS_MS };
  Object.entries(overrides).forEach(([key, value]) => {
    if (isTimeBound(value)) {
      merged[key] = value;
    }
  });
  return merged;
};

export const getOperationTimeBound = (
  operation: string,
  config?: ApiConfig
): TimeBound => {
  return resolveOperationTimeBounds(config)[operation] ?? {
    still_working_ms: 5000,
    fail_ms: 20000,
  };
};
