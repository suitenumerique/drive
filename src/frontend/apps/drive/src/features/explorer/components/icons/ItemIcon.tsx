import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import folderIcon from "@/assets/folder/folder.svg";
import folderRestrictedIcon from "@/assets/folder/folder-restricted.svg";
import {
  FileIcon,
  FileIconContent,
  getExtensionFromName,
  getMimeCategory,
  ICONS,
  IconSize,
  MimeCategory,
} from "@gouvfr-lasuite/ui-components";
import { itemToPreviewFile } from "../../utils/utils";

type ItemIconProps = {
  item: Item;
  size?: IconSize;
  type?: "mini" | "normal";
  alt?: string;
};

// Global icon component for all items, same logic as the one in the ui-kit ( FileIcon )
// but provide support for folders.
export const ItemIcon = ({
  item,
  size = IconSize.MEDIUM,
  type = "normal",
  alt,
}: ItemIconProps) => {
  const extendedIcon = getItemExtendedIcon(item, type);
  if (alt) {
    const preview = itemToPreviewFile(item);
    const mimeCategory = preview.isFolderAccessDenied
      ? MimeCategory.DENIED
      : getMimeCategory(
          preview.mimetype,
          getExtensionFromName(preview.title),
        );
    const iconSrc = extendedIcon ?? ICONS[type][mimeCategory];

    return (
      <img
        src={iconSrc}
        alt={alt}
        draggable={false}
        className={`c__file-icon icon--${size}`}
      />
    );
  }
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
  if (item.is_restricted || item.type === ItemType.RESTRICTION) {
    return folderRestrictedIcon.src;
  }

  if (item.type === ItemType.FOLDER) {
    return folderIcon.src;
  }

  const uploadState = item.upload_state;
  if (uploadState === ItemUploadState.SUSPICIOUS) {
    return ICONS[type][MimeCategory.SUSPICIOUS];
  }

  return null;
};
