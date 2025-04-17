import { Item, TreeItem } from "@/features/drivers/types";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { TreeViewNodeTypeEnum, useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { useRouter } from "next/router";

export const useDeleteTreeNode = () => {
  const treeContext = useTreeContext<TreeItem>();
  const router = useRouter();
  const deleteTreeNode = (nodeId: string) => {
    const nodes = treeContext?.treeData.nodes;
    const node = treeContext?.treeData.getNode(nodeId);
    if (!node) return;

    const isWorkspace = itemIsWorkspace(node as Item);
    if (nodes?.length === 5 && isWorkspace) {
      treeContext?.treeData.deleteNodes(["SEPARATOR", "SHARED_SPACE", nodeId]);
    } else {
      treeContext?.treeData.deleteNode(nodeId);
    }
    if (node.nodeType === TreeViewNodeTypeEnum.NODE) {
      const parentId = node.parentId;
      if (parentId) {
        router.push(`/explorer/items/${parentId}`);
      }
    }
  };

  return { deleteTreeNode };
};
