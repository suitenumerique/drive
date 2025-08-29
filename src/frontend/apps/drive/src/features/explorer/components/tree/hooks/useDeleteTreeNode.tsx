import { Item, TreeItem } from "@/features/drivers/types";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";

export const useDeleteTreeNode = () => {
  const treeContext = useTreeContext<TreeItem>();

  const deleteTreeNode = (
    nodeId: string,
    redirectToParent: boolean = false
  ) => {
    const nodes = treeContext?.treeData.nodes;
    const node = treeContext?.treeData.getNode(nodeId);
    if (!node) return;

    const isWorkspace = itemIsWorkspace(node as Item);
    if (nodes?.length === 5 && isWorkspace) {
      treeContext?.treeData.deleteNodes(["SEPARATOR", "SHARED_SPACE", nodeId]);
    } else if (!redirectToParent) {
      treeContext?.treeData.deleteNode(nodeId);
    }
  };

  return { deleteTreeNode };
};
