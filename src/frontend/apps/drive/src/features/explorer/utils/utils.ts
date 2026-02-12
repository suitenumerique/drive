import { getDriver } from "@/features/config/Config";
import {
  Item,
  ItemType,
  ItemUploadState,
  LinkReach,
  WorkspaceType,
} from "@/features/drivers/types";
import i18n from "@/features/i18n/initI18n";
import { FilePreviewType } from "@/features/ui/preview/files-preview/FilesPreview";
import { DefaultRoute } from "@/utils/defaultRoutes";

export const SESSION_STORAGE_KEY_FROM_ROUTE = "fromRoute";
export const SESSION_STORAGE_KEY_MANUAL_NAVIGATION_ITEM_ID =
  "manualNavigationItemId";

export const setFromRoute = (fromRoute: DefaultRoute) => {
  sessionStorage.setItem(SESSION_STORAGE_KEY_FROM_ROUTE, fromRoute);
};

export const clearFromRoute = () => {
  sessionStorage.removeItem(SESSION_STORAGE_KEY_FROM_ROUTE);
};

export const getFromRoute = () => {
  return sessionStorage.getItem(
    SESSION_STORAGE_KEY_FROM_ROUTE,
  ) as DefaultRoute | null;
};

export const setManualNavigationItemId = (itemId: string) => {
  sessionStorage.setItem(SESSION_STORAGE_KEY_MANUAL_NAVIGATION_ITEM_ID, itemId);
};

export const getManualNavigationItemId = () => {
  return sessionStorage.getItem(
    SESSION_STORAGE_KEY_MANUAL_NAVIGATION_ITEM_ID,
  ) as string | null;
};

/**
 * Temporary solution to redirect to the last visited item, by default the personal root folder.
 * But we are waiting for the backend to be ready to handle this.
 *
 * TODO: Use localStorage maybe
 */
export const gotoLastVisitedItem = async (prefix: string = "") => {
  const item = await getLastVisitedItem();
  if (!item) {
    console.error("No items found, so cannot redirect to last visited item");
    return;
  }
  window.location.href = `${prefix}/explorer/items/${item.id}`;
};

export const getLastVisitedItem = async () => {
  const { children: items } = await getDriver().getItems({
    type: ItemType.FOLDER,
  });
  if (!items.length) {
    return null;
  }
  const main = items.find((item) => item.main_workspace);
  if (main) {
    return main;
  }
  return items[0];
};

/** TODO: test */
export const timeAgo = (date: Date) => {
  if (!date) {
    return "";
  }
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);

  if (years > 0) {
    return i18n.t("time.years_ago", { count: years });
  } else if (months > 0) {
    return i18n.t("time.months_ago", { count: months });
  } else if (weeks > 0) {
    return i18n.t("time.weeks_ago", { count: weeks });
  } else if (days > 0) {
    return i18n.t("time.days_ago", { count: days });
  } else if (hours > 0) {
    return i18n.t("time.hours_ago", { count: hours });
  } else if (minutes > 0) {
    return i18n.t("time.minutes_ago", { count: minutes > 0 ? minutes : 1 });
  }
  return i18n.t("time.seconds_ago");
};

/** TODO: test */
export const getExtension = (item: Item, useTitle = false) => {
  const str = useTitle ? item.title : item.filename;
  return getExtensionFromName(str);
};

export const getExtensionFromName = (str: string) => {
  if (!str) {
    return null;
  }
  const parts = str.split(".");
  if (parts.length === 1) {
    return null;
  }
  return parts.pop()!;
};

export const formatSize = (size: number) => {
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let convertedSize = size;
  let unitIndex = 0;

  while (convertedSize >= 1024 && unitIndex < units.length - 1) {
    convertedSize /= 1024;
    unitIndex++;
  }

  return `${
    convertedSize < 10
      ? convertedSize.toFixed(2)
      : convertedSize < 100
        ? convertedSize.toFixed(1)
        : Math.round(convertedSize)
  } ${units[unitIndex]}`;
};

export const getParentIdFromPath = (path?: string) => {
  if (!path) {
    return undefined;
  }
  const clonedPath = path + "";
  const parts = clonedPath.split(".");
  if (parts.length === 1) {
    return undefined;
  }
  return parts[parts.length - 2];
};

export const getWorkspaceType = (item: Item): WorkspaceType => {
  if (item.main_workspace) {
    return WorkspaceType.MAIN;
  }
  if (item.link_reach === LinkReach.PUBLIC && item.user_roles?.length === 0) {
    return WorkspaceType.PUBLIC;
  }
  return WorkspaceType.SHARED;
};

/**
 * Check if a given ID is part of an item's tree via its path
 * @param itemPath - The path of the item (e.g., "id1.id2.id3")
 * @param targetId - The ID to check if it's in the tree
 * @returns true if the targetId is part of the item's tree, false otherwise
 */
export const isIdInItemTree = (itemPath: string, targetId: string): boolean => {
  if (!itemPath || !targetId) {
    return false;
  }

  // Split the path into individual IDs
  const pathIds = itemPath.split(".");

  // Check if the targetId exists anywhere in the path
  return pathIds.includes(targetId);
};

export const getItemTitle = (item: Item) => {
  if (item.main_workspace) {
    return i18n.t("explorer.workspaces.mainWorkspace");
  }
  return item.title;
};

export const itemToPreviewFile = (item: Item) => {
  return {
    id: item.id,
    title: item.title,
    mimetype: item.mimetype ?? "",
    url_preview: item.url_preview ?? "",
    url: item.url ?? "",
    isSuspicious: item.upload_state === ItemUploadState.SUSPICIOUS,
    is_wopi_supported: item.is_wopi_supported,
    size: item.size,
  } as FilePreviewType;
};
