import { TreeItem } from "@/features/drivers/types";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";

export const useDeleteTreeNode = () => {
  const treeContext = useTreeContext<TreeItem>();

  const deleteTreeNode = (
    nodeId: string,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _redirectToParent: boolean = false
  ) => {
    // Get the node to delete
    const node = treeContext?.treeData.getNode(nodeId);
    if (!node) return; // If the node is not found, return

    const parentId = treeContext?.treeData.getParentId(nodeId);

    if (parentId !== "SHARED_SPACE" && parentId !== "PUBLIC_SPACE") {
      treeContext?.treeData.deleteNode(nodeId);

      return;
    }

    const checkRootNode = (parentKey: string): boolean => {
      const rootNode = treeContext?.treeData.getNode(parentKey);
      console.log("rootNode", rootNode);
      if (!rootNode) return false;
      const isChildOfShared = rootNode?.children?.some(
        (child) => child.id === nodeId
      );
      if (!isChildOfShared) return false;
      const isLastChild = rootNode.children?.length === 1;
      treeContext?.treeData.deleteNode(nodeId);
      if (isLastChild) {
        treeContext?.treeData.deleteNode(parentKey);
      }
      return true;
    };

    const isSharedLastChild = checkRootNode("SHARED_SPACE");
    if (!isSharedLastChild) {
      checkRootNode("PUBLIC_SPACE");
    }
  };

  return { deleteTreeNode };
};
