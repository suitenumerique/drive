import { useCallback, useEffect, useMemo, useState } from "react";
import { ColumnType, SortState } from "../types/columns";
import { ViewConfig } from "../types/viewConfig";
import { VIEW_CONFIGS } from "../config/viewConfigs";
import { COLUMN_REGISTRY } from "../config/columnRegistry";
import { useColumnPreferences } from "./useColumnPreferences";
import { computeOrdering } from "../utils/ordering";
import { DefaultRoute } from "@/utils/defaultRoutes";

type ViewConfigKey = DefaultRoute | "folder";

export function useGridColumns(
  viewConfigKey: ViewConfigKey,
  navigationId?: string,
) {
  const { prefs, setColumn } = useColumnPreferences();
  const [sortState, setSortState] = useState<SortState>(null);

  const viewConfig: ViewConfig =
    VIEW_CONFIGS[viewConfigKey] ?? VIEW_CONFIGS.folder;

  // Reset sort on view or folder navigation change
  useEffect(() => {
    setSortState(null);
  }, [viewConfigKey, navigationId]);

  const cycleSortForColumn = useCallback(
    (columnId: "title" | ColumnType) => {
      setSortState((prev) => {
        if (!prev || prev.columnId !== columnId) {
          return { columnId, direction: "asc" };
        }
        if (prev.direction === "asc") {
          return { columnId, direction: "desc" };
        }
        return null;
      });
    },
    [],
  );

  const col1Config = COLUMN_REGISTRY[prefs.column1];
  const col2Config = COLUMN_REGISTRY[prefs.column2];

  const ordering = useMemo(
    () => computeOrdering(viewConfig, sortState),
    [viewConfig, sortState],
  );

  return {
    col1Config,
    col2Config,
    sortState,
    cycleSortForColumn,
    setColumn,
    prefs,
    ordering,
    viewConfig,
  };
}
