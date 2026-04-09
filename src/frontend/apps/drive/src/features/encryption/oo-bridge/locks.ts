/**
 * Lock management for OnlyOffice collaboration.
 *
 * Tracks cell/range locks (spreadsheets) and document-level save locks.
 * Locks are broadcast to all peers via the relay and applied locally.
 */

/** A cell/range lock (spreadsheets) */
export interface CellLock {
  userId: string;
  block: unknown; // OnlyOffice block descriptor (cell range)
  timestamp: number;
}

/** Save lock — prevents concurrent checkpoints */
export interface SaveLockState {
  holder: string | null; // userId of the lock holder, null if free
  since: number | null;
}

// --- Cell/range locks ---

const cellLocks = new Map<string, CellLock>();

/**
 * Acquire a cell/range lock.
 * Returns false if the range is already locked by another user.
 */
export function acquireCellLock(
  lockId: string,
  userId: string,
  block: unknown
): boolean {
  const existing = cellLocks.get(lockId);
  if (existing && existing.userId !== userId) {
    return false; // Already locked by someone else
  }
  cellLocks.set(lockId, { userId, block, timestamp: Date.now() });
  return true;
}

/**
 * Release a cell/range lock.
 */
export function releaseCellLock(lockId: string, userId: string): void {
  const existing = cellLocks.get(lockId);
  if (existing?.userId === userId) {
    cellLocks.delete(lockId);
  }
}

/**
 * Release all locks held by a user (e.g. when they disconnect).
 */
export function releaseAllUserLocks(userId: string): void {
  for (const [lockId, lock] of cellLocks.entries()) {
    if (lock.userId === userId) {
      cellLocks.delete(lockId);
    }
  }
}

/**
 * Get all active cell locks.
 */
export function getAllCellLocks(): Map<string, CellLock> {
  return new Map(cellLocks);
}

/**
 * Get locks held by a specific user.
 */
export function getUserCellLocks(userId: string): CellLock[] {
  return Array.from(cellLocks.values()).filter(l => l.userId === userId);
}

// --- Save lock ---

const saveLock: SaveLockState = { holder: null, since: null };

/**
 * Try to acquire the save lock for checkpointing.
 * Only one user can hold the save lock at a time.
 */
export function acquireSaveLock(userId: string): boolean {
  if (saveLock.holder && saveLock.holder !== userId) {
    // Check if the lock is stale (> 60 seconds)
    if (saveLock.since && Date.now() - saveLock.since > 60_000) {
      // Force release stale lock
      saveLock.holder = null;
      saveLock.since = null;
    } else {
      return false;
    }
  }
  saveLock.holder = userId;
  saveLock.since = Date.now();
  return true;
}

/**
 * Release the save lock.
 */
export function releaseSaveLock(userId: string): void {
  if (saveLock.holder === userId) {
    saveLock.holder = null;
    saveLock.since = null;
  }
}

/**
 * Check if the save lock is held.
 */
export function isSaveLocked(): boolean {
  return saveLock.holder !== null;
}

/**
 * Get save lock state.
 */
export function getSaveLockState(): SaveLockState {
  return { ...saveLock };
}

/**
 * Reset all locks (used on disconnect/reconnect).
 */
export function resetAllLocks(): void {
  cellLocks.clear();
  saveLock.holder = null;
  saveLock.since = null;
}
