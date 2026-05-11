import { Item, ItemUploadState } from "@/features/drivers/types";
import { getMimeCategory, MimeCategory } from "@gouvfr-lasuite/ui-kit";
import { getExtension } from "../utils/utils";

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
