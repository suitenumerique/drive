import { Item, ItemType } from '@/features/drivers/types';
import { Driver } from '@/features/drivers/Driver';
import { FlatNode } from './types';

/**
 * Fetch the full subtree (including folders) and enrich each node with its
 * parent id (within the subtree), depth from root, and a `/`-joined title
 * breadcrumb of its ancestors (root included, self excluded).
 *
 * `Item.path` is an ltree of dot-separated uuids from the tree's topmost
 * ancestor down to the item. We use it to reconstruct parent links without
 * an extra request.
 */
export async function fetchSubtree(
  driver: Driver,
  root: Item,
): Promise<FlatNode[]> {
  if (root.type !== ItemType.FOLDER) {
    return [{ item: root, parentId: null, depth: 0, pathCrumb: '' }];
  }

  const items = await driver.getDescendants(root.id);
  const byId = new Map<string, Item>();
  for (const it of items) byId.set(it.id, it);

  const rootDepth = root.path.split('.').length;

  return items.map((it) => {
    if (it.id === root.id) {
      return { item: it, parentId: null, depth: 0, pathCrumb: '' };
    }
    const segments = it.path.split('.');
    const parentUuid = segments[segments.length - 2];
    // Crumb is the titles of ancestors from the root (inclusive) down to
    // the item's direct parent (inclusive). Self is excluded.
    const crumbUuids = segments.slice(rootDepth - 1, segments.length - 1);
    const crumbTitles = crumbUuids.map(
      (uuid) => byId.get(uuid)?.title ?? '?',
    );
    return {
      item: it,
      parentId: parentUuid === root.id ? null : parentUuid,
      depth: segments.length - rootDepth,
      pathCrumb: crumbTitles.join(' / '),
    };
  });
}

export const filesOnly = (nodes: FlatNode[]): FlatNode[] =>
  nodes.filter((n) => n.item.type === ItemType.FILE);

export const foldersOnly = (nodes: FlatNode[]): FlatNode[] =>
  nodes.filter((n) => n.item.type === ItemType.FOLDER);

/**
 * Return descendants of `rootId` that are already encryption roots in their
 * own right (stacked encryption). These items — and everything under them —
 * must be left untouched when encrypting the outer root: they keep their
 * existing per-user ItemAccess entries and their own key chain.
 */
export const innerEncryptionRoots = (
  nodes: FlatNode[],
  rootId: string,
): FlatNode[] =>
  nodes.filter(
    (n) => n.item.id !== rootId && !!n.item.is_encryption_root,
  );

/**
 * Test whether `node` belongs to the subtree rooted at any of `innerRoots`
 * (the inner root itself counts as inside its own subtree).
 */
export const isInsideInnerRoot = (
  node: FlatNode,
  innerRoots: FlatNode[],
): boolean => {
  for (const inner of innerRoots) {
    if (node.item.id === inner.item.id) return true;
    if (node.item.path.startsWith(inner.item.path + '.')) return true;
  }
  return false;
};

/**
 * Compute the chain of wrapped folder keys needed for the vault to reach
 * the parent of `node` when wrapping/unwrapping. Ancestors are listed from
 * the root's direct child down to the node's direct parent (both
 * ancestors inclusive), with the root and the node itself excluded.
 *
 * For a direct child of the root, the chain is empty — the entry key (the
 * root's per-user wrapped key) is already the parent.
 */
export function chainForNode(
  node: FlatNode,
  rootId: string,
  folderWrappedKeys: Map<string, ArrayBuffer>,
): ArrayBuffer[] {
  const segments = node.item.path.split('.');
  const rootIdx = segments.indexOf(rootId);
  if (rootIdx === -1) return [];
  const intermediateIds = segments.slice(rootIdx + 1, segments.length - 1);
  const chain: ArrayBuffer[] = [];
  for (const id of intermediateIds) {
    const wk = folderWrappedKeys.get(id);
    if (!wk) {
      throw new Error(
        `Missing wrapped key for ancestor folder ${id} — folder ordering bug.`,
      );
    }
    chain.push(wk);
  }
  return chain;
}
