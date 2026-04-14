import { Item, ItemType } from '@/features/drivers/types';
import { Driver } from '@/features/drivers/Driver';
import { FlatNode } from './types';

export async function fetchSubtree(
  driver: Driver,
  root: Item,
): Promise<FlatNode[]> {
  if (root.type !== ItemType.FOLDER) {
    return [{ item: root, parentId: null, depth: 0, pathCrumb: '' }];
  }

  const items = await driver.getDescendants(root.id);
  return items.map((it) =>
    it.id === root.id
      ? { item: it, parentId: null, depth: 0, pathCrumb: '' }
      : { item: it, parentId: null, depth: 1, pathCrumb: root.title },
  );
}

export const filesOnly = (nodes: FlatNode[]): FlatNode[] =>
  nodes.filter((n) => n.item.type === ItemType.FILE);
