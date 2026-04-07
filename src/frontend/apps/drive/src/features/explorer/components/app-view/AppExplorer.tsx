import { Item } from "@/features/drivers/types";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { ItemFilters } from "@/features/drivers/Driver";
import { EmbeddedExplorerGridActionsCellProps } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridActionsCell";
import { NavigationEvent } from "@/features/explorer/components/GlobalExplorerContext";
import { AppExplorerInner } from "./AppExplorerInner";
import {
  ColumnConfig,
  ColumnPreferences,
  ColumnType,
  SortState,
} from "../../types/columns";
import { useGridColumns } from "../../hooks/useGridColumns";
import { computeFilters } from "../../utils/ordering";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { ViewConfig } from "../../types/viewConfig";

export interface AppExplorerProps {
  // View configuration
  viewConfigKey: DefaultRoute | "folder";
  navigationId?: string;
  defaultBaseFilters?: ItemFilters;
  onComputedFiltersChange?: (filters: ItemFilters) => void;
  // Data
  childrenItems?: Item[];
  gridActionsCell?: (
    params: EmbeddedExplorerGridActionsCellProps
  ) => React.ReactNode;
  disableItemDragAndDrop?: boolean;
  gridHeader?: React.ReactNode;
  selectionBarActions?: React.ReactNode;
  // Override the default onNavigate from ExplorerContext
  onNavigate?: (event: NavigationEvent) => void;
  // Override the default onFileClick (e.g. to prevent preview in trash)
  onFileClick?: (item: Item) => void;
  disableAreaSelection?: boolean;
  canSelect?: (item: Item) => boolean;
  // Infinite scroll props
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  isLoading?: boolean;
  isMinimalLayout?: boolean;
  showFilters?: boolean;
}

export type AppExplorerContextType = AppExplorerProps & {
  sortState: SortState;
  onSort: (columnId: "title" | ColumnType) => void;
  prefs: ColumnPreferences;
  onChangeColumn: (slot: "column1" | "column2", type: ColumnType) => void;
  column1Config?: ColumnConfig;
  column2Config?: ColumnConfig;
  filters: ItemFilters;
  onFiltersChange: (filters: ItemFilters) => void;
  viewConfig: ViewConfig;
};

export const AppExplorerContext = createContext<
  AppExplorerContextType | undefined
>(undefined);

export const useAppExplorer = () => {
  const context = useContext(AppExplorerContext);
  if (!context) {
    throw new Error(
      "useAppExplorer must be used within an AppExplorerProvider"
    );
  }
  return context;
};

export const AppExplorer = (props: AppExplorerProps) => {
  const [baseFilters, setBaseFilters] = useState<ItemFilters>(
    props.defaultBaseFilters ?? {}
  );

  const {
    column1Config,
    column2Config,
    sortState,
    cycleSortForColumn,
    setColumn,
    prefs,
    viewConfig,
  } = useGridColumns(props.viewConfigKey, props.navigationId);

  const computedFilters = useMemo(
    () => computeFilters(viewConfig, baseFilters, sortState),
    [viewConfig, baseFilters, sortState],
  );

  const onComputedFiltersChangeRef = useRef(props.onComputedFiltersChange);
  onComputedFiltersChangeRef.current = props.onComputedFiltersChange;

  useEffect(() => {
    onComputedFiltersChangeRef.current?.(computedFilters);
  }, [computedFilters]);

  const contextValue: AppExplorerContextType = useMemo(
    () => ({
      ...props,
      sortState,
      onSort: cycleSortForColumn,
      prefs,
      onChangeColumn: setColumn,
      column1Config,
      column2Config,
      filters: baseFilters,
      onFiltersChange: setBaseFilters,
      viewConfig,
    }),
    [
      props,
      sortState,
      cycleSortForColumn,
      prefs,
      setColumn,
      column1Config,
      column2Config,
      baseFilters,
    ],
  );

  return (
    <AppExplorerContext.Provider value={contextValue}>
      <AppExplorerInner />
    </AppExplorerContext.Provider>
  );
};
