import { Item, ItemType } from "./types";

export const isFolder = (item: Item) =>
  item.type === ItemType.FOLDER || item.type === ItemType.RESTRICTION;

export const isUnavailableRestriction = (
  item: Pick<Item, "type" | "target">,
) =>
  item.type === ItemType.RESTRICTION &&
  (!item.target?.can_access || item.target.deleted);

// Resolve the identity for navigation; the destination page loads its own data.
export const getNavigableItem = (item: Item): Item | undefined => {
  if (isUnavailableRestriction(item)) return undefined;
  if (item.type !== ItemType.RESTRICTION || !item.target) return item;
  return { ...item, id: item.target.id, originalId: item.target.id };
};

export const itemIsWorkspace = (item: Item) => {
  if (item.main_workspace) {
    return false;
  }
  return (
    item.type === ItemType.FOLDER && item.path.split(".").length === 1
  );
};
