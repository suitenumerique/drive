import { getDriver } from "@/features/config/Config";
import { Item, ItemType } from "@/features/drivers/types";
import i18n from "@/features/i18n/initI18n";
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
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let convertedSize = size;
  let unitIndex = 0;
  
  while (convertedSize >= 1024 && unitIndex < units.length - 1) {
    convertedSize /= 1024;
    unitIndex++;
  }
  
  return `${convertedSize < 10 ? convertedSize.toFixed(2) : convertedSize < 100 ? convertedSize.toFixed(1) : Math.round(convertedSize)} ${units[unitIndex]}`;
};
