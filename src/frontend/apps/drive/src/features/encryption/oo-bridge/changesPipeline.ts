/**
 * Change processing pipeline for OnlyOffice patches.
 *
 * Handles the bridge between OnlyOffice's internal change format and
 * the network layer (ChainPad or direct broadcast).
 */

import type { OOChange, OOMessage } from './types';

let patchIndex = 0;

/**
 * Reset the patch index (called when loading a checkpoint).
 */
export function resetPatchIndex(index: number = 0): void {
  patchIndex = index;
}

/**
 * Get the current patch index.
 */
export function getPatchIndex(): number {
  return patchIndex;
}

/**
 * Normalize an OnlyOffice change into the standard format.
 *
 * CryptPad's parseChanges() — inner.js:1340-1355
 */
export function parseChange(
  change: unknown,
  ooId: string
): OOChange {
  return {
    docid: 'fresh',
    change: JSON.stringify(change),
    time: Date.now(),
    user: ooId,
    useridoriginal: ooId,
  };
}

/**
 * Parse an array of raw OnlyOffice changes.
 */
export function parseChanges(
  changes: unknown[],
  ooId: string
): OOChange[] {
  return changes.map(c => parseChange(c, ooId));
}

/**
 * Handle changes coming FROM OnlyOffice (user made edits).
 *
 * Returns the parsed changes ready to be encrypted and broadcast.
 *
 * CryptPad's handleChanges() — inner.js:1357-1443
 */
export function handleOutgoingChanges(
  msg: OOMessage,
  ooId: string
): OOChange[] | null {
  if (msg.type !== 'saveChanges' || !msg.changes) {
    return null;
  }

  // OnlyOffice sends changes as a JSON string, not an array
  const rawChanges: unknown[] =
    typeof msg.changes === 'string'
      ? JSON.parse(msg.changes)
      : msg.changes;

  const parsed = parseChanges(rawChanges, ooId);
  patchIndex += parsed.length;
  return parsed;
}

/**
 * Handle changes coming FROM the network (other users' edits).
 *
 * Returns the changes in the format OnlyOffice expects to receive.
 *
 * CryptPad's fromOOHandler routing — inner.js:1538-1640
 */
export function handleIncomingChanges(rawChanges: OOChange[]): OOMessage {
  patchIndex += rawChanges.length;
  // Live collaboration changes use 'saveChanges' (not 'authChanges' which is only for initial load).
  // OO's _onSaveChanges handler expects changesIndex and locks fields.
  return {
    type: 'saveChanges',
    changes: rawChanges,
    changesIndex: patchIndex,
    locks: [],
    excelAdditionalInfo: null,
  } as OOMessage;
}

/**
 * Process an event from OnlyOffice (via the fromOOHandler callback).
 *
 * Routes different event types to appropriate handlers.
 * Returns an action descriptor for the caller to handle.
 */
export function processOOEvent(msg: OOMessage): {
  action:
    | 'broadcast_changes'
    | 'lock_request'
    | 'cursor_update'
    | 'save_lock_check'
    | 'noop';
  data?: unknown;
} {
  switch (msg.type) {
    case 'saveChanges':
      return { action: 'broadcast_changes', data: msg.changes };
    case 'getLock':
      return { action: 'lock_request', data: msg.locks };
    case 'cursor':
      return { action: 'cursor_update', data: msg.cursor };
    case 'isSaveLock':
      return { action: 'save_lock_check' };
    case 'getMessages':
      // Chat messages — not implemented, return empty
      return { action: 'noop' };
    default:
      return { action: 'noop' };
  }
}
