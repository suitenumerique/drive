import { Item, TreeItem, TreeItemData } from "@/features/drivers/types";
import {
  IconSize,
  NodeRendererProps,
  TreeDataItem,
  TreeViewDataType,
  TreeViewItem,
  TreeViewNodeTypeEnum,
} from "@gouvfr-lasuite/ui-kit";
import { DroppableNodeTree } from "./DroppableNodeTree";
import {
  NavigationEventType,
  useGlobalExplorer,
} from "../GlobalExplorerContext";
import { useModal } from "@openfun/cunningham-react";
import { ExplorerTreeItemActions } from "./ExplorerTreeItemActions";
import { ExplorerEditWorkspaceModal } from "../modals/workspaces/ExplorerEditWorkspaceModal";
import { ItemIcon } from "../icons/ItemIcon";
import publicSpaceIcon from "@/assets/folder/folder-tiny-public.svg";
import sharedSpaceIcon from "@/assets/folder/folder-tiny-shared.svg";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { WorkspaceCategory } from "../../constants";

type ExplorerTreeItemProps = NodeRendererProps<TreeDataItem<TreeItem>>;

export const ExplorerTreeItem = ({ ...props }: ExplorerTreeItemProps) => {
  const { onNavigate } = useGlobalExplorer();
  const item: TreeViewDataType<TreeItemData> = props.node.data.value;
  const editModal = useModal();

  return (
    <>
      <DroppableNodeTree id={props.node.id} item={item} nodeTree={props}>
        <TreeViewItem
          {...props}
          onClick={() => {
            if (item.nodeType === TreeViewNodeTypeEnum.SIMPLE_NODE) {
              return;
            }
            onNavigate({
              type: NavigationEventType.ITEM,
              item: item as Item,
            });
          }}
        >
          <div className="explorer__tree__item" data-testid="tree_item_content">
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
              {item.nodeType === TreeViewNodeTypeEnum.SIMPLE_NODE && (
                <span className="explorer__tree__item__title">
                  {item.label}
                </span>
              )}
            </div>

            {item?.nodeType === TreeViewNodeTypeEnum.NODE && (
              <ExplorerTreeItemActions item={item as Item} />
            )}
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
  if (item.nodeType === TreeViewNodeTypeEnum.SIMPLE_NODE) {
    const isPublcNode = item.id === WorkspaceCategory.PUBLIC_SPACE;
    const isSharedNode = item.id === WorkspaceCategory.SHARED_SPACE;
    if (isPublcNode) {
      return <img src={publicSpaceIcon.src} alt="" />;
    }
    if (isSharedNode) {
      return <img src={sharedSpaceIcon.src} alt="" />;
    }
  }

  if (item.nodeType === TreeViewNodeTypeEnum.NODE) {
    const isWorkspace = itemIsWorkspace(item as Item);
    const isMainWorkspace = item.main_workspace;
    const isSimpleFolder = !isWorkspace && !isMainWorkspace;
    return (
      <ItemIcon
        item={item as Item}
        type="mini"
        isTree
        size={isSimpleFolder ? IconSize.SMALL : IconSize.X_SMALL}
      />
    );
  }

  return null;
};
