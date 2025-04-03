import { Item, TreeItem } from "@/features/drivers/types";
import folderIcon from "@/assets/tree/folder.svg";
import {
  NodeRendererProps,
  TreeDataItem,
  TreeViewItem,
  TreeViewNodeTypeEnum,
} from "@gouvfr-lasuite/ui-kit";
import { DroppableNodeTree } from "./DroppableNodeTree";
import { NavigationEventType, useExplorer } from "../ExplorerContext";
import { useModal } from "@openfun/cunningham-react";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import { ExplorerTreeItemActions } from "./ExplorerTreeItemActions";

type ExplorerTreeItemProps = NodeRendererProps<TreeDataItem<TreeItem>>;

export const ExplorerTreeItem = ({ ...props }: ExplorerTreeItemProps) => {
  const { onNavigate } = useExplorer();
  const item = props.node.data.value as TreeItem;
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
              <img src={folderIcon.src} alt="folder" />
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
