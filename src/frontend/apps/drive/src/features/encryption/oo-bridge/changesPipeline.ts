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

/**
 * Track an INCOMING saveChanges envelope against our local `patchIndex`
 * WITHOUT mutating the envelope. Called right before we hand the
 * message to OO so the receiver's local counter stays in sync with the
 * absolute `changesIndex` OO will observe from the replay stream.
 *
 * This is the "seed from first event" strategy: instead of rewriting
 * every incoming envelope's index to our local counter, we adopt the
 * sender's counter as our own. For single-sender replay (the normal
 * case), this preserves whatever internal cross-references OO may hold
 * against absolute indices while still keeping outgoing changes from
 * us sequenced after the stream we've observed.
 */
export function observeIncomingSaveChanges(
  msg: Record<string, unknown>,
): void {
  if (msg.type !== 'saveChanges') return;
  const incoming = Number(msg.changesIndex);
  if (Number.isFinite(incoming) && incoming > patchIndex) {
    patchIndex = incoming;
  }
}
