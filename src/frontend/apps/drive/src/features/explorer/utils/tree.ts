import { Item } from "@/features/drivers/types";

/**
 * From a tree and a given currentItem, it returns the list of ancestors of the currentItem.
 * If the currentItem is not found in the tree, it throws an error.
 */
export const getAncestors = (tree: Item, currentItem: Item): Item[] => {
  const aux = (treeItem: Item, ancestors: Item[]): Item[] | undefined => {
    ancestors = [...ancestors];
    ancestors.push(treeItem);
    if (treeItem.id === currentItem.id) {
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
    throw new Error("Ancestors not found");
  }
  return ancestors;
};
