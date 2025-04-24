import { Item } from "@/features/drivers/types";
import { ExplorerInner } from "./ExplorerInner";
import { ExplorerGridActionsCellProps } from "./grid/ExplorerGridActionsCell";
import { createContext, useContext } from "react";
import { ItemFilters } from "@/features/drivers/Driver";
import { NavigationEvent } from "./ExplorerContext";

export interface ExplorerProps {
  childrenItems?: Item[];
  gridActionsCell?: (params: ExplorerGridActionsCellProps) => React.ReactNode;
  disableItemDragAndDrop?: boolean;
  gridHeader?: JSX.Element;
  selectionBarActions?: JSX.Element;
  filters?: ItemFilters;
  onFiltersChange?: (filters: ItemFilters) => void;
  // Override the default onNavigate from ExplorerContext
  onNavigate?: (event: NavigationEvent) => void;
}

export type ExplorerInnerType = ExplorerProps;

export const ExplorerInnerContext = createContext<
  ExplorerInnerType | undefined
>(undefined);

export const useExplorerInner = () => {
  const context = useContext(ExplorerInnerContext);
  if (!context) {
    throw new Error(
      "useExplorerInner must be used within an ExplorerInnerProvider"
    );
  }
  return context;
};

export const Explorer = (props: ExplorerProps) => {
  return (
    <ExplorerInnerContext.Provider value={props}>
      <ExplorerInner {...props} />
    </ExplorerInnerContext.Provider>
  );
};
