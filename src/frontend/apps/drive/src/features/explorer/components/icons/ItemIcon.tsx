import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import folderIcon from "@/assets/folder/folder.svg";
import { ICONS } from "../../utils/mimeTypes";
import {
  FileIcon,
  FileIconContent,
  IconSize,
  MimeCategory,
} from "@gouvfr-lasuite/ui-kit";
import { itemToPreviewFile } from "../../utils/utils";

type ItemIconProps = {
  item: Item;
  size?: IconSize;
  type?: "mini" | "normal";
};

// Global icon component for all items, same logic as the one in the ui-kit ( FileIcon )
// but provide support for folders.
export const ItemIcon = ({
  item,
  size = IconSize.MEDIUM,
  type = "normal",
}: ItemIconProps) => {
  const extendedIcon = getItemExtendedIcon(item, type);
  if (extendedIcon) {
    return <FileIconContent icon={extendedIcon} size={size} />;
  }
  return <FileIcon file={itemToPreviewFile(item)} size={size} />;
};

/**
 * The ui-kit already provides lots of icons for different mime types, but
 * on drive we support additional icons for suspicious items and folders.
 *
 * This function returns the appropriate icon for those extended cases, if
 * the item is not an extended case, it returns null. That way we can use the
 * ui-kit icon as a fallback.
 */
export const getItemExtendedIcon = (
  item: Item,
  type: "normal" | "mini",
): string | null => {
  if (item.type === ItemType.FOLDER) {
    return folderIcon.src;
  }

  const uploadState = item.upload_state;
  if (uploadState === ItemUploadState.SUSPICIOUS) {
    return ICONS[type][MimeCategory.SUSPICIOUS];
  }

  return null;
};
