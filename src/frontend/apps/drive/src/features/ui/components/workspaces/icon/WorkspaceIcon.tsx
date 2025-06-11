import { getContainerSize, Icon, IconSize } from "@gouvfr-lasuite/ui-kit";
import { useMemo } from "react";

type WorkspaceIconProps = {
  isMainWorkspace?: boolean;
  iconSize?: IconSize;
};

export const WorkspaceIcon = ({
  isMainWorkspace = false,
  iconSize = IconSize.MEDIUM,
}: WorkspaceIconProps) => {
  const containerSize = useMemo(() => getContainerSize(iconSize), [iconSize]);

  const iconName = useMemo(() => {
    if (isMainWorkspace) {
      return "person";
    }
    return "groups";
  }, [isMainWorkspace]);

  const style = {
    width: containerSize,
    height: containerSize,
  };

  return (
    <div className="workspace-icon-container" style={style}>
      <Icon name={iconName} size={iconSize} color="white" />
    </div>
  );
};
