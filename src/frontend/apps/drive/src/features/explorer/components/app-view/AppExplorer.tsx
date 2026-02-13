import { Item } from "@/features/drivers/types";
import { createContext, useContext } from "react";
import { ItemFilters } from "@/features/drivers/Driver";
import { EmbeddedExplorerGridActionsCellProps } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridActionsCell";
import { NavigationEvent } from "@/features/explorer/components/GlobalExplorerContext";
import { AppExplorerInner } from "./AppExplorerInner";

export interface AppExplorerProps {
  childrenItems?: Item[];
  gridActionsCell?: (
    params: EmbeddedExplorerGridActionsCellProps
  ) => React.ReactNode;
  disableItemDragAndDrop?: boolean;
  gridHeader?: React.ReactNode;
  selectionBarActions?: React.ReactNode;
  filters?: ItemFilters;
  onFiltersChange?: (filters: ItemFilters) => void;
  // Override the default onNavigate from ExplorerContext
  onNavigate?: (event: NavigationEvent) => void;
  disableAreaSelection?: boolean;
  canSelect?: (item: Item) => boolean;
  // Infinite scroll props
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  isLoading?: boolean;
  isMinimalLayout?: boolean;
  showFilters?: boolean;
  // Custom empty placeholder when no items
  emptyPlaceholder?: React.ReactNode;
}

export type AppExplorerType = AppExplorerProps;

export const AppExplorerContext = createContext<AppExplorerType | undefined>(
  undefined
);

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
  return (
    <AppExplorerContext.Provider value={props}>
      <AppExplorerInner {...props} />
    </AppExplorerContext.Provider>
  );
};
