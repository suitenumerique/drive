import { Item, TreeItem } from "@/features/drivers/types";
import folderIcon from "@/assets/tree/folder.svg";
import workspaceIcon from "@/assets/tree/workspace.svg";
import mainWorkspaceIcon from "@/assets/tree/main-workspace.svg";
import {
  NodeRendererProps,
  TreeDataItem,
  TreeViewDataType,
  TreeViewItem,
  TreeViewNodeTypeEnum,
} from "@gouvfr-lasuite/ui-kit";
import { DroppableNodeTree } from "./DroppableNodeTree";
import { NavigationEventType, useExplorer } from "../ExplorerContext";
import { useModal } from "@openfun/cunningham-react";
import { ExplorerTreeItemActions } from "./ExplorerTreeItemActions";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";

type ExplorerTreeItemProps = NodeRendererProps<TreeDataItem<TreeItem>>;

export const ExplorerTreeItem = ({ ...props }: ExplorerTreeItemProps) => {
  const { onNavigate } = useExplorer();
  const item = props.node.data.value;
  const editModal = useModal();

  return (
    <>
      <DroppableNodeTree id={props.node.id} item={item} nodeTree={props}>
        <TreeViewItem
          {...props}
          onClick={() => {
            onNavigate({
              type: NavigationEventType.ITEM,
              item: item as Item,
            });
          }}
        >
          <div className="explorer__tree__item">
            <div className="explorer__tree__item__content">
              <ExplorerTreeItemIcon item={item} size={16} />
              {/* 
                We need to check the nodeType because the generic type T in TreeViewDataType 
                is only available for nodes of type NODE
              */}
              {item.nodeType === TreeViewNodeTypeEnum.NODE && (
                <span className="explorer__tree__item__title">
                  {item.title}
                </span>
              )}
            </div>
            <ExplorerTreeItemActions item={item as Item} />
          </div>
          {editModal.isOpen && (
            <ExplorerEditWorkspaceModal
              {...editModal}
              item={item as Item}
              onClose={() => {
                editModal.close();
              }}
            />
          )}
        </TreeViewItem>
      </DroppableNodeTree>
    </>
  );
};

export const ExplorerTreeItemIcon = ({
  item,
  size = 16,
}: {
  item: TreeViewDataType<TreeItem>;
  size?: number;
}) => {
  const isMainWorkspace =
    item.nodeType === TreeViewNodeTypeEnum.NODE && item.main_workspace;
  const isWorkspace = itemIsWorkspace(item as Item);
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
