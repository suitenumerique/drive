import { Item } from "@/features/drivers/types";
import { ExplorerInner } from "./ExplorerInner";

export interface ExplorerProps {
  childrenItems?: Item[];
}

export const Explorer = (props: ExplorerProps) => {
  return <ExplorerInner {...props} />;
};
