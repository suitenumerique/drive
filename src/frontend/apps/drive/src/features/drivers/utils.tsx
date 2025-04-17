import { Item, ItemType } from "./types";

export const itemIsWorkspace = (item: Item) => {
  if (item.main_workspace) {
    return false;
  }
  return item.type === ItemType.FOLDER && item.path.split(".").length === 1;
};
