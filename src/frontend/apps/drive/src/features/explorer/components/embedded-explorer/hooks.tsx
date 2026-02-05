import { Item } from "@/features/drivers/types";
import { useEmbeddedExplorerGirdContext } from "./EmbeddedExplorerGrid";

export const useDisableDragGridItem = (item: Item) => {
  const { selectedItemsMap, disableItemDragAndDrop } =
    useEmbeddedExplorerGirdContext();
  const isSelected = !!selectedItemsMap[item.id];
  return disableItemDragAndDrop || !isSelected;
};
