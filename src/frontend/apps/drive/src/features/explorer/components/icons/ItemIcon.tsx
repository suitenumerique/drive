import { Item, ItemType } from "@/features/drivers/types";
import folderIcon from "@/assets/folder/folder.svg";
import folderIconTree from "@/assets/tree/folder.svg";
import folderPersonalIcon from "@/assets/folder/folder-tiny-perso.svg";
import {
  getItemMimeCategory,
  getMimeCategory,
  ICONS,
} from "../../utils/mimeTypes";
import { itemIsWorkspace } from "@/features/drivers/utils";
import {
  getContainerSize,
  getIconSize,
  Icon,
  IconSize,
} from "@gouvfr-lasuite/ui-kit";
import { useMemo } from "react";
import { FilePreviewType } from "@/features/ui/preview/files-preview/FilesPreview";
import { getExtensionFromName } from "../../utils/utils";

type ItemIconProps = {
  item: Item;
  size?: IconSize;
  type?: "mini" | "normal";
  isTree?: boolean;
};

// Global icon component for all items
export const ItemIcon = ({
  item,
  size = IconSize.MEDIUM,
  type = "normal",
  isTree = false,
}: ItemIconProps) => {
  const isWorkspace = itemIsWorkspace(item) || item.main_workspace;

  if (isWorkspace) {
    return (
      <WorkspaceIcon isMainWorkspace={item.main_workspace} iconSize={size} />
    );
  }

  const mimeIcon = getItemIcon(item, type, isTree);
  const imgSize = getIconSize(size);

  return (
    <img
      src={mimeIcon.src}
      alt=""
      className={`item-icon ${size}`}
      width={imgSize}
      height={imgSize}
      draggable="false"
    />
  );
};

type WorkspaceIconProps = {
  isMainWorkspace?: boolean;
  iconSize?: IconSize;
};

// Workspace icon component
export const WorkspaceIcon = ({
  isMainWorkspace = false,
  iconSize = IconSize.MEDIUM,
}: WorkspaceIconProps) => {
  const containerSize = useMemo(() => getContainerSize(iconSize), [iconSize]);

  const style = {
    width: containerSize,
    height: containerSize,
  };

  if (isMainWorkspace) {
    return (
      <img
        src={folderPersonalIcon.src}
        alt=""
        width={containerSize}
        height={containerSize}
      />
    );
  }

  return (
    <div className="workspace-icon-container" style={style}>
      <Icon name="groups" size={iconSize} color="white" />
    </div>
  );
};

export const getItemIcon = (
  item: Item,
  type: "normal" | "mini",
  isTree: boolean
) => {
  if (item.type === ItemType.FOLDER) {
    return isTree ? folderIconTree : folderIcon;
  }
  const category = getItemMimeCategory(item);
  return ICONS[type][category];
};

export const getIconByMimeType = (
  mimeType: string,
  type: "normal" | "mini"
) => {
  const category = getMimeCategory(mimeType);
  return ICONS[type][category];
};

/**
 * Used by the FilePreview component to display the file icon.
 * The FilePreview only uses FilePreviewType, not Item, so it needs a
 * dedicated component to display the file icon.
 */
export const FileIcon = ({
  file,
  size = "medium",
  type = "normal",
}: {
  file: FilePreviewType;
  size?: "small" | "medium" | "large" | "xlarge";
  type?: "mini" | "normal";
}) => {
  const category = getMimeCategory(
    file.mimetype,
    getExtensionFromName(file.title)
  );
  const icon = ICONS[type][category];

  return (
    <img
      src={icon.src}
      alt=""
      className={`item-icon ${size}`}
      draggable="false"
    />
  );
};
