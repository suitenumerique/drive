import { Item } from "@/features/drivers/types";
import { useExplorerGridItems } from "./ExplorerGridItems";

export const useDisableDragGridItem = (item: Item) => {
  const { selectedItemsMap, disableItemDragAndDrop } = useExplorerGridItems();
  const isSelected = !!selectedItemsMap[item.id];
  return disableItemDragAndDrop || !isSelected || !item.abilities.move;
};
