import { Item } from "@/features/drivers/types";
import { itemIsWorkspace } from "@/features/drivers/utils";
import workspaceIcon from "@/assets/tree/workspace.svg";
import mainWorkspaceIcon from "@/assets/tree/main-workspace.svg";
import folderIcon from "@/assets/tree/folder.svg";

type ExplorerItemIconProps = {
  item: Item;
  size?: number;
};

export const ExplorerItemIcon = ({
  item,
  size = 16,
}: ExplorerItemIconProps) => {
  const isMainWorkspace = item.main_workspace;
  const isWorkspace = itemIsWorkspace(item);
  if (isMainWorkspace) {
    return (
      <img
        width={size}
        height={size}
        src={mainWorkspaceIcon.src}
        alt="folder"
      />
    );
  }

  if (isWorkspace) {
    return (
      <img width={size} height={size} src={workspaceIcon.src} alt="folder" />
    );
  }

  return <img width={size} height={size} src={folderIcon.src} alt="folder" />;
};
