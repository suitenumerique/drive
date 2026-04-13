import { Item, ItemType } from '@/features/drivers/types';
import { FlatNode } from './types';

/**
 * Walks a tree returned by driver.getTree and produces a flat list of all
 * descendant items (files + folders), including the root itself.
 */
export function flattenSubtree(root: Item): FlatNode[] {
  const out: FlatNode[] = [];

  const walk = (
    node: Item,
    parentId: string | null,
    depth: number,
    pathCrumb: string,
  ) => {
    out.push({ item: node, parentId, depth, pathCrumb });

    if (node.type === ItemType.FOLDER && node.children?.length) {
      const nextCrumb = pathCrumb ? `${pathCrumb} / ${node.title}` : node.title;
      for (const child of node.children) {
        walk(child, node.id, depth + 1, nextCrumb);
      }
    }
  };

  walk(root, null, 0, '');
  return out;
}

export const filesOnly = (nodes: FlatNode[]): FlatNode[] =>
  nodes.filter((n) => n.item.type === ItemType.FILE);
