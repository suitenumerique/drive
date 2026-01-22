import { useTreeContext, TreeDataItem, TreeViewDataType, TreeViewNodeTypeEnum } from "@gouvfr-lasuite/ui-kit";
import { TreeItem, TreeItemData } from "@/features/drivers/types";

/**
 * Hook providing utility functions for tree operations.
 * These functions help manage tree items, especially for favorites
 * where the same item can appear multiple times in the tree.
 */
export const useTreeUtils = () => {
  const treeContext = useTreeContext<TreeItem>();

  /**
   * Recursively finds all tree IDs that match a given original item ID.
   * This is useful for finding all occurrences of the same item in the tree
   * (e.g., when an item appears both as a favorite and as a child of another favorite).
   *
   * @param originalId - The original item ID to search for
   * @returns An array of tree IDs that match the original ID
   */
  const findAllTreeIdsByOriginalId = (originalId: string): string[] => {
    const matchingIds: string[] = [];

    const searchNodes = (
      nodes: TreeDataItem<TreeViewDataType<TreeItem>>[]
    ): void => {
      for (const node of nodes) {
        const nodeValue = node.value as TreeViewDataType<TreeItemData>;
        
        // Check if this node's originalId matches
        if (
          nodeValue.nodeType === TreeViewNodeTypeEnum.NODE &&
          (nodeValue as TreeItemData).originalId === originalId
        ) {
          matchingIds.push(node.value.id);
        }

        // Recursively search children
        if (node.children && node.children.length > 0) {
          searchNodes(node.children);
        }
      }
    };

    if (treeContext?.treeData.nodes) {
      searchNodes(treeContext.treeData.nodes);
    }

    console.log("matchingIds", matchingIds);

    return matchingIds;
  };

  /**
   * Deletes all occurrences of an item from the tree by its original ID.
   * This handles the case where the same item appears multiple times
   * (e.g., as a favorite and as a child of another opened favorite folder).
   *
   * @param originalId - The original item ID to delete
   * @returns The number of nodes deleted
   */
  const deleteAllByOriginalId = (originalId: string): number => {
    const treeIds = findAllTreeIdsByOriginalId(originalId);
    treeContext?.treeData.deleteNodes(treeIds);
    return treeIds.length;
  };

  return {
    findAllTreeIdsByOriginalId,
    deleteAllByOriginalId,
  };
};
