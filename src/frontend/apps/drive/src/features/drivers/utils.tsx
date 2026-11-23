import { Item, ItemType } from "./types";

export const isFolder = (item: Item) =>
  item.type === ItemType.FOLDER || item.type === ItemType.RESTRICTION;

export const isLink = (item: Pick<Item, "type">) =>
  item.type === ItemType.LINK;

// Only web URLs are ever opened, never javascript: or data: ones.
export const isWebUrl = (url: string | null | undefined): url is string =>
  !!url && /^https?:\/\//i.test(url);

// A link points outside of Drive: open it in a new tab that cannot reach back
// to the opener nor learn where it was opened from.
export const openLink = (item: Pick<Item, "link_url">) => {
  if (isWebUrl(item.link_url)) {
    window.open(item.link_url, "_blank", "noopener,noreferrer");
  }
};

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

// A restriction is a location entry standing for its actual folder. Returns
// that folder, with its own permissions, when the user can reach it.
export const getRestrictionTarget = (item: Item): Item | undefined => {
  if (item.type !== ItemType.RESTRICTION || !item.target) return undefined;
  if (isUnavailableRestriction(item)) return undefined;
  return {
    ...item,
    ...item.target,
    originalId: item.target.id,
    type: ItemType.FOLDER,
    target: null,
  };
};

// Drops on a restriction go into its actual folder, when it can be reached.
export const getDropTarget = (item: Item): Item | undefined => {
  if (item.type !== ItemType.RESTRICTION) return item;
  return getRestrictionTarget(item);
};

export const itemIsWorkspace = (item: Item) => {
  if (item.main_workspace) {
    return false;
  }
  return (
    item.type === ItemType.FOLDER && item.path.split(".").length === 1
  );
};
