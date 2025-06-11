import { Item, TreeItem } from "@/features/drivers/types";
import {
  IconSize,
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
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import { ExplorerItemIcon } from "../ExplorerFolderIcon";
import { itemIsWorkspace } from "@/features/drivers/utils";

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
              <ExplorerTreeItemIcon item={item} size={IconSize.SMALL} />
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
}: {
  item: TreeViewDataType<TreeItem>;
  size?: IconSize;
}) => {
  if (item.nodeType === TreeViewNodeTypeEnum.NODE) {
    const isWorkspace = itemIsWorkspace(item as Item) || item.main_workspace;
    return (
      <ExplorerItemIcon
        item={item as Item}
        size={isWorkspace ? IconSize.X_SMALL : IconSize.SMALL}
      />
    );
  }

  return null;
};
