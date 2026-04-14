import { Item } from "@/features/drivers/types";
import { useEmbeddedExplorerGirdContext } from "./EmbeddedExplorerGrid";
import { useIsItemSelected } from "@/features/explorer/stores/selectionStore";

export const useDisableDragGridItem = (item: Item) => {
  const { disableItemDragAndDrop } = useEmbeddedExplorerGirdContext();
  const isSelected = useIsItemSelected(item.id);
  return disableItemDragAndDrop || !isSelected;
};
