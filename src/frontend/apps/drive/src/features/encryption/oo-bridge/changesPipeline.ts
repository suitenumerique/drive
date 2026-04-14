import type { OOChange, OOMessage } from './types';

let patchIndex = 0;

export function resetPatchIndex(index: number = 0): void {
  patchIndex = index;
}

export function getPatchIndex(): number {
  return patchIndex;
}

function parseChange(change: unknown, ooId: string): OOChange {
  return {
    docid: 'fresh',
    change: JSON.stringify(change),
    time: Date.now(),
    user: ooId,
    useridoriginal: ooId,
  };
}

/**
 * Take an outgoing OO `saveChanges` message and return a message-shaped object
 * we can ship over the relay verbatim. Each element of `changes` is wrapped
 * with author metadata; every other field on the OO message is preserved
 * unchanged so the receiver gets the same context the sender's OO produced.
 */
export function wrapOutgoingSaveChanges(
  msg: OOMessage,
  ooId: string,
): Record<string, unknown> | null {
  if (msg.type !== 'saveChanges' || !msg.changes) return null;

  const rawChanges: unknown[] =
    typeof msg.changes === 'string'
      ? JSON.parse(msg.changes as unknown as string)
      : (msg.changes as unknown[]);

  const wrappedChanges = rawChanges.map(c => parseChange(c, ooId));
  patchIndex += wrappedChanges.length;

  return {
    ...(msg as unknown as Record<string, unknown>),
    changes: wrappedChanges,
    changesIndex: patchIndex,
    syncChangesIndex: patchIndex,
  };
}
