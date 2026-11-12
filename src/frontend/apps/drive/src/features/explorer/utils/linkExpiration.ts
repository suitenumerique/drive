import { Item, LinkReach, LinkRole } from "@/features/drivers/types";

const LINK_REACH_PRIORITY: Record<LinkReach, number> = {
  [LinkReach.RESTRICTED]: 0,
  [LinkReach.AUTHENTICATED]: 1,
  [LinkReach.PUBLIC]: 2,
};

const LINK_ROLE_PRIORITY: Record<LinkRole, number> = {
  [LinkRole.READER]: 0,
  [LinkRole.EDITOR]: 1,
};

type ItemLink = Pick<
  Item,
  | "link_reach"
  | "link_role"
  | "link_expires_at"
  | "ancestors_link_reach"
  | "ancestors_link_role"
>;

export const isLinkExpired = (
  item: Pick<Item, "link_expires_at">,
  now = new Date(),
) => !!item.link_expires_at && new Date(item.link_expires_at) <= now;

// An expired link reads as restricted, but the backend keeps its past date
// when a link update omits it: reopening the link must drop it as well.
export const getLinkExpirationReset = (
  item: Pick<Item, "link_expires_at">,
): { link_expires_at?: null } =>
  isLinkExpired(item) ? { link_expires_at: null } : {};

// The backend combines the item link with the one inherited from its parents
// and keeps the widest. An expiration only closes the item's own link, so it
// has an effect only when that link opens more than the inherited one.
export const canLinkExpire = (item: ItemLink) => {
  const reach = item.link_reach ?? LinkReach.RESTRICTED;
  if (reach === LinkReach.RESTRICTED) {
    return false;
  }
  const inheritedReach = item.ancestors_link_reach ?? LinkReach.RESTRICTED;
  if (reach !== inheritedReach) {
    return LINK_REACH_PRIORITY[reach] > LINK_REACH_PRIORITY[inheritedReach];
  }
  if (!item.link_role || !item.ancestors_link_role) {
    return false;
  }
  return (
    LINK_ROLE_PRIORITY[item.link_role] >
    LINK_ROLE_PRIORITY[item.ancestors_link_role]
  );
};
