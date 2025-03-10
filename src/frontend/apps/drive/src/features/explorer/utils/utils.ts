import { getDriver } from "@/features/config/Config";
import { ItemType } from "@/features/drivers/types";
/**
 * Temporary solution to redirect to the last visited item, by default the personal root folder.
 * But we are waiting for the backend to be ready to handle this.
 *
 * TODO: Use localStorage maybe
 */
export const gotoLastVisitedItem = async () => {
  const items = await getDriver().getItems({ type: ItemType.FOLDER });
  if (!items.length) {
    console.error("No items found, so cannot redirect to last visited item");
    return;
  }
  window.location.href = `/explorer/items/${items[0].id}`;
};
