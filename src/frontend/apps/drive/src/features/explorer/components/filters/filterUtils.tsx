import { ItemFilters } from "@/features/drivers/Driver";
import { presetRange, applyDateRange } from "../../utils/dateFilters";
export const ALL = "all";

export const handleFilterChange = (
  filters: ItemFilters = {},
  name: string,
  value: unknown,
) => {
  if (value === ALL || !value) {
    const newFilters = { ...filters };
    delete newFilters[name as keyof ItemFilters];
    return newFilters;
  } else {
    return { ...filters, [name]: value };
  }
};

/**
 * This function converts the filters object to a query params object.
 */
export const convertFiltersToQueryParams = (
  filters: ItemFilters,
): Omit<ItemFilters, "modified"> => {
  let newFilters = { ...filters };

  /**
   * Modified filter.
   */
  delete newFilters.modified;
  const actualDateRange =
    filters.modified?.customRange ?? presetRange(filters.modified?.key);
  newFilters = applyDateRange(newFilters, actualDateRange);

  return newFilters;
};
