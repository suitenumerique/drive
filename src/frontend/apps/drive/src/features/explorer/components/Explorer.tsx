import { Item } from "@/features/drivers/types";
import { ExplorerInner } from "./ExplorerInner";
import { ExplorerGridActionsCellProps } from "./grid/ExplorerGridActionsCell";
import { createContext, useContext } from "react";

export interface ExplorerProps {
  childrenItems?: Item[];
  gridActionsCell?: (params: ExplorerGridActionsCellProps) => JSX.Element;
  disableItemDragAndDrop?: boolean;
  gridHeader?: JSX.Element;
  selectionBarActions?: JSX.Element;
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
