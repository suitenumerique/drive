import React from "react";
import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { IconProps } from "@/features/ui/components/icon/Icon";

export enum ColumnType {
  LAST_MODIFIED = "last_modified",
  CREATED = "created",
  CREATED_BY = "created_by",
  FILE_TYPE = "file_type",
  FILE_SIZE = "file_size",
}

export type SortDirection = "asc" | "desc";

export type SortState = {
  columnId: "title" | ColumnType;
  direction: SortDirection;
} | null;

export type ColumnPreferences = {
  column1: ColumnType;
  column2: ColumnType;
};

export const DEFAULT_COLUMN_PREFERENCES: ColumnPreferences = {
  column1: ColumnType.LAST_MODIFIED,
  column2: ColumnType.CREATED_BY,
};

export type ColumnCellProps = CellContext<Item, unknown>;

export type ColumnConfig = {
  type: ColumnType;
  labelKey: string;
  icon: React.ComponentType<IconProps>;
  orderingField: string;
  cell: React.FC<ColumnCellProps>;
};

// COLUMN_REGISTRY is populated in columns.registry.ts after cell components are created (Task 5)
// This avoids circular imports between types and components.
