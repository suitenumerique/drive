import { Item, ItemTreeItem } from "@/features/drivers/types";
import { TreeDataItem, TreeViewDataType } from "@gouvfr-lasuite/ui-kit";

/**
 * From a tree and a given currentItem, it returns the list of ancestors of the currentItem.
 * If the currentItem is not found in the tree, it throws an error.
 */
export const getAncestors = (tree: TreeDataItem<TreeViewDataType<ItemTreeItem>>, currentItem: Item): Item[] => {
  const aux = (treeItem: TreeDataItem<TreeViewDataType<ItemTreeItem>>, ancestors: ItemTreeItem[]): ItemTreeItem[] | undefined => {
    ancestors = [...ancestors];
    
    ancestors.push(treeItem.value as ItemTreeItem);
    if (treeItem.value.id === currentItem.id) {
      return ancestors;
    }
    if (treeItem.children) {
      for (const child of treeItem.children) {
        const childAncestors = aux(child, ancestors);
        if (childAncestors) {
          return childAncestors;
        }
      }
    }
  };
  const ancestors = aux(tree, []);
  if (!ancestors) {
    return []
  }
  return ancestors;
};
