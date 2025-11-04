import { Item, TreeItem } from "@/features/drivers/types";
import {
  TreeViewDataType,
  TreeViewNodeTypeEnum,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { itemToTreeItem } from "../../GlobalExplorerContext";
import { WorkspaceCategory } from "../../../constants";

export const useAddWorkspaceNode = () => {
  const treeContext = useTreeContext<TreeItem>();
  const { t } = useTranslation();
  const addWorkspaceNode = (data: Item) => {
    const sharedNode = treeContext?.treeData.getNode(
      WorkspaceCategory.SHARED_SPACE
    );
    if (!sharedNode) {
      const publicWorkspaceNode: TreeViewDataType<TreeItem> = {
        id: WorkspaceCategory.SHARED_SPACE,
        nodeType: TreeViewNodeTypeEnum.SIMPLE_NODE,
        childrenCount: 1,
        label: t("explorer.tree.shared_space"),
        children: [itemToTreeItem(data)],
        pagination: {
          currentPage: 1,
          hasMore: false,
        },
      };
      treeContext?.treeData.addRootNode(publicWorkspaceNode, 1);
    } else {
      treeContext?.treeData.addChild(
        WorkspaceCategory.SHARED_SPACE,
        itemToTreeItem(data),
        0
      );
    }
  };

  return { addWorkspaceNode };
};
