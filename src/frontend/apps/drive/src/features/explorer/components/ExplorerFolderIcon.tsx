import { Item } from "@/features/drivers/types";
import { itemIsWorkspace } from "@/features/drivers/utils";
import folderIcon from "@/assets/tree/folder.svg";
import { WorkspaceIcon } from "@/features/ui/components/workspaces/icon/WorkspaceIcon";
import { useMemo } from "react";

import { getIconSize, IconSize } from "@gouvfr-lasuite/ui-kit";

type ExplorerItemIconProps = {
  item: Item;
  size?: IconSize;
};

export const ExplorerItemIcon = ({
  item,
  size = IconSize.MEDIUM,
}: ExplorerItemIconProps) => {
  const isMainWorkspace = item.main_workspace;
  const isWorkspace = itemIsWorkspace(item);

  const imgSize = useMemo(() => getIconSize(size), [size]);

  if (isMainWorkspace) {
    return <WorkspaceIcon isMainWorkspace iconSize={size} />;
  }

  if (isWorkspace) {
    return <WorkspaceIcon iconSize={size} />;
  }

  return (
    <img width={imgSize} height={imgSize} src={folderIcon.src} alt="folder" />
  );
};
