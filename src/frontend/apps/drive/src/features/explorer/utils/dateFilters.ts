import { ItemFilters } from "@/features/drivers/Driver";

export type DatePreset =
  | "today"
  | "last_7_days"
  | "last_30_days"
  | "this_year"
  | "more_than_a_year";

export type DateRange = Pick<
  ItemFilters,
  "updated_at_after" | "updated_at_before"
>;

const pad = (value: number) => String(value).padStart(2, "0");

/**
 * Format a date as a local YYYY-MM-DD string, matching the date-only bounds the
 * backend filter expects (it compares on the date part, whole-day inclusive).
 */
export const toISODate = (date: Date): string =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

const addDays = (date: Date, days: number): Date => {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
};

/**
 * Compute the modification date range for a preset, today included as the upper
 * bound. `today` is injectable for deterministic tests.
 */
export const presetRange = (preset: DatePreset, today: Date = new Date()): DateRange => {
  if (preset === "more_than_a_year") {
    const before = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
    return { updated_at_before: toISODate(before) };
  }

  let after: Date;
  switch (preset) {
    case "today":
      after = today;
      break;
    case "last_7_days":
      after = addDays(today, -6);
      break;
    case "last_30_days":
      after = addDays(today, -29);
      break;
    case "this_year":
      after = new Date(today.getFullYear(), 0, 1);
      break;
  }
  return {
    updated_at_after: toISODate(after),
    updated_at_before: toISODate(today),
  };
};

/** Replace the modification date bounds of the filters with the given range. */
export const applyDateRange = (
  filters: ItemFilters,
  range: DateRange | null,
): ItemFilters => {
  const next = { ...filters };
  delete next.updated_at_after;
  delete next.updated_at_before;
  return { ...next, ...(range ?? {}) };
};

/** Extract the modification date range from the filters, or null when unset. */
export const dateRangeFromFilters = (filters: ItemFilters): DateRange | null => {
  if (!filters.updated_at_after && !filters.updated_at_before) {
    return null;
  }
  return {
    updated_at_after: filters.updated_at_after,
    updated_at_before: filters.updated_at_before,
  };
};
