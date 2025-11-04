import { TreeItem } from "@/features/drivers/types";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { WorkspaceCategory } from "../../../constants";

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

    if (
      parentId !== WorkspaceCategory.SHARED_SPACE &&
      parentId !== WorkspaceCategory.PUBLIC_SPACE
    ) {
      treeContext?.treeData.deleteNode(nodeId);

      return;
    }

    // This function checks if the node to be deleted is a direct child of the root "shared" or "public" nodes.
    // If it is, it deletes the node. If that root node only had this single child,
    // it also deletes the root node itself (removing the shared/public section from the tree when empty).
    const checkRootNode = (parentKey: string): boolean => {
      const rootNode = treeContext?.treeData.getNode(parentKey);

      if (!rootNode) return false;

      // Check if nodeId is a direct child of the given root node (shared/public section)
      const isChildOfRoot = rootNode?.children?.some(
        (child) => child.id === nodeId
      );

      if (!isChildOfRoot) return false;

      // If this is the last child, we will remove the root as well
      const isLastChild = rootNode.children?.length === 1;

      // Delete the target node from the tree
      treeContext?.treeData.deleteNode(nodeId);

      // If it was the last child, remove the section/root node as well
      if (isLastChild) {
        treeContext?.treeData.deleteNode(parentKey);
      }

      return true;
    };

    const isSharedLastChild = checkRootNode(WorkspaceCategory.SHARED_SPACE);
    if (!isSharedLastChild) {
      checkRootNode(WorkspaceCategory.PUBLIC_SPACE);
    }
  };

  return { deleteTreeNode };
};
