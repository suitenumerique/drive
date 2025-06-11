import { Item, ItemType } from "@/features/drivers/types";
import folderIcon from "@/assets/folder/folder.svg";

import { getMimeCategory, ICONS } from "../utils/mimeTypes";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { ExplorerItemIcon } from "./ExplorerFolderIcon";
import { IconSize } from "@gouvfr-lasuite/ui-kit";

type ItemIconProps = {
  item: Item;
  size?: IconSize;
  type?: "mini" | "normal";
};

export const ItemIcon = ({
  item,
  size = IconSize.MEDIUM,
  type = "normal",
}: ItemIconProps) => {
  const isWorkspace = itemIsWorkspace(item) || item.main_workspace;

  if (isWorkspace) {
    return <ExplorerItemIcon item={item} size={IconSize.SMALL} />;
  }

  const mimeIcon = getItemIcon(item, type);

  return (
    <img
      src={mimeIcon.src}
      alt=""
      className={`item-icon ${size}`}
      draggable="false"
    />
  );
};

export const getItemIcon = (item: Item, type: "normal" | "mini") => {
  if (item.type === ItemType.FOLDER) {
    return folderIcon;
  }
  const category = getMimeCategory(item);
  return ICONS[type][category];
};
