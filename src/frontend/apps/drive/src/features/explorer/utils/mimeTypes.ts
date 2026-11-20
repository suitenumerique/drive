import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import { getMimeCategory, MimeCategory } from "@gouvfr-lasuite/ui-components";
import { getExtension } from "../utils/utils";

const ITEM_ICON_ALT_KEYS: Partial<Record<MimeCategory, string>> = {
  [MimeCategory.SQLITE]: "explorer.grid.item_icon_alt.sqlite",
  [MimeCategory.GRIST]: "explorer.grid.item_icon_alt.grist",
};

/**
 * Wrapper around the ui-kit getMimeCategory function to add support for
 * suspicious items.
 */
export const getItemMimeCategory = (item: Item): MimeCategory => {
  const mimetype = item.mimetype;
  const extension = getExtension(item);
  const uploadState = item.upload_state;
  if (uploadState === ItemUploadState.SUSPICIOUS) {
    return MimeCategory.SUSPICIOUS;
  }

  if (!mimetype) {
    return MimeCategory.OTHER;
  }

  return getMimeCategory(mimetype, extension);
};

export const getFormatTranslationKey = (item: Item) => {
  const category = getItemMimeCategory(item);
  return `mime.${category}`;
};

/**
 * Text alternative for a file or folder type icon.
 * Null means the icon is decorative: the visible label already ends with the
 * file extension, so announcing the type again would repeat it.
 */
export const getItemIconAltKey = (
  item: Item,
  visibleLabel: string,
): string | null => {
  if (item.is_restricted || item.type === ItemType.RESTRICTION) {
    return "explorer.grid.item_icon_alt.restricted_folder";
  }

  if (item.type === ItemType.FOLDER) {
    return "explorer.grid.columns.folder";
  }

  if (item.upload_state === ItemUploadState.SUSPICIOUS) {
    return "explorer.grid.item_icon_alt.suspicious";
  }

  // The icon is chosen from the title, which is also the text on screen.
  const extension = getExtension(item, true);
  if (
    extension &&
    visibleLabel.toLowerCase().endsWith(`.${extension.toLowerCase()}`)
  ) {
    return null;
  }

  const category = getMimeCategory(item.mimetype ?? "", extension);
  return ITEM_ICON_ALT_KEYS[category] ?? `mime.${category}`;
};
