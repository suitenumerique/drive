import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import folderIcon from "@/assets/folder/folder.svg";
import {
  FileIcon,
  FileIconContent,
  getIconSize,
  ICONS,
  IconSize,
  MimeCategory,
} from "@gouvfr-lasuite/ui-components";
import { itemToPreviewFile } from "../../utils/utils";
import { getEffectiveMimetype } from "../../utils/mimeTypes";

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
  const icon = extendedIcon ? (
    <FileIconContent icon={extendedIcon} size={size} />
  ) : (
    <FileIcon
      file={{
        ...itemToPreviewFile(item),
        // Encrypted uploads are stored as application/octet-stream since the
        // server cannot inspect ciphertext: pick the icon from the extension.
        mimetype: getEffectiveMimetype(item) ?? "",
      }}
      size={size}
    />
  );

  if (!item.is_encrypted) {
    return icon;
  }

  return (
    <span style={{ position: "relative", display: "inline-flex" }}>
      {icon}
      <span
        className="material-icons drive__encryption-badge"
        style={{
          fontSize: Math.max(12, Math.round(getIconSize(size) * 0.4)),
        }}
        aria-hidden="true"
      >
        verified_user
      </span>
    </span>
  );
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
