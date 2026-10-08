import { Item, ItemType } from "./types";

export const isFolder = (item: Item) =>
  item.type === ItemType.FOLDER || item.type === ItemType.RESTRICTION;

// A restricted folder may still be accessible through a direct grant.
// Deleted or missing targets remain unavailable rather than asking for access.
export const isFolderAccessDenied = (item: Pick<Item, "type" | "target">) =>
  item.type === ItemType.RESTRICTION &&
  item.target?.can_access === false &&
  !item.target.deleted;

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

// A restriction is a location entry; drops go into its actual folder.
export const getDropTarget = (item: Item): Item | undefined => {
  if (isUnavailableRestriction(item)) return undefined;
  if (item.type !== ItemType.RESTRICTION || !item.target) return item;
  return {
    ...item,
    ...item.target,
    originalId: item.target.id,
    type: ItemType.FOLDER,
    target: null,
  };
};

export const itemIsWorkspace = (item: Item) => {
  if (item.main_workspace) {
    return false;
  }
  return (
    item.type === ItemType.FOLDER && item.path.split(".").length === 1
  );
};
