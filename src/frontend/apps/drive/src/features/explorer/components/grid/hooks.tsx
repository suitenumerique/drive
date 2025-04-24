import { Item } from "@/features/drivers/types";
import { useExplorer } from "../ExplorerContext";
import { useExplorerInner } from "../Explorer";

export const useDisableDragGridItem = (item: Item) => {
  const { selectedItemsMap } = useExplorer();
  const { disableItemDragAndDrop } = useExplorerInner();
  const isSelected = !!selectedItemsMap[item.id];
  return disableItemDragAndDrop || !isSelected || !item.abilities.move;
};
