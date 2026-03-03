import { ItemFilters } from "@/features/drivers/Driver";
import { ItemType } from "@/features/drivers/types";
import { ColumnType, SortState } from "../types/columns";
import { ViewConfig } from "../types/viewConfig";

const COLUMN_ORDERING_FIELDS: Record<ColumnType, string> = {
  [ColumnType.LAST_MODIFIED]: "updated_at",
  [ColumnType.CREATED]: "created_at",
  [ColumnType.CREATED_BY]: "creator__full_name",
  [ColumnType.FILE_TYPE]: "mime_category",
  [ColumnType.FILE_SIZE]: "size",
};

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
      : COLUMN_ORDERING_FIELDS[sortState.columnId];

  const prefix = sortState.direction === "desc" ? "-" : "";

  return `${prefix}${field}`;
}

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
