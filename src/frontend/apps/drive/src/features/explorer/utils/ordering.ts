import { ItemFilters } from "@/features/drivers/Driver";
import { ItemType } from "@/features/drivers/types";
import { SortState } from "../types/columns";
import { ViewConfig } from "../types/viewConfig";
import { COLUMN_REGISTRY } from "../config/columnRegistry";

/**
 * Builds the ordering string for the API from view config and current sort state.
 * Returns the view's default ordering when no explicit sort is active.
 */
export function computeOrdering(
  viewConfig: ViewConfig,
  sortState: SortState,
): string {
  if (!sortState) {
    return viewConfig.defaultOrdering;
  }

  const field =
    sortState.columnId === "title"
      ? "title"
      : COLUMN_REGISTRY[sortState.columnId].orderingField;

  const prefix = sortState.direction === "desc" ? "-" : "";

  return `${prefix}${field}`;
}

/**
 * Merges base filters with computed ordering and view-specific constraints
 * (e.g. files-only mode adds a type filter).
 */
export function computeFilters(
  viewConfig: ViewConfig,
  baseFilters: ItemFilters,
  sortState: SortState,
): ItemFilters {
  const ordering = computeOrdering(viewConfig, sortState);

  const filters: ItemFilters = {
    ...baseFilters,
    ordering,
  };

  if (viewConfig.folderMode === "files_only") {
    filters.type = ItemType.FILE;
  }

  return filters;
}
