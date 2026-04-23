/**
 * Replicated Word-document lock table, arbitrated via the relay's total
 * order (server-stamped monotonic `timestampMs` on every binary frame).
 *
 * Why this exists
 * ---------------
 * OnlyOffice's Word editor calls `askLock(paragraphId)` before any
 * structural mutation (splitting a paragraph via Enter, changing a
 * style, inserting a table…). In the upstream OO deployment, a central
 * Document Server answers that call and grants or denies based on its
 * in-memory lock table. In our E2E-encrypted setup there's no central
 * server, so every tab runs a fake Document Server locally that used
 * to auto-grant unconditionally — fine for single-user, broken for
 * concurrent editors: both tabs think they own the same paragraph,
 * produce divergent structural edits, and OO crashes the moment the
 * patches collide on a resource one side doesn't recognise.
 *
 * How arbitration works
 * ---------------------
 * 1. Peer A asks to claim a set of paragraph keys.
 * 2. We send an encrypted `oo:lockRequest` frame through the relay.
 *    The relay stamps it with a strictly-monotonic `timestampMs`.
 * 3. The relay ACKs with `frame:settled { timestampMs }`. TCP FIFO on
 *    our socket means every earlier relay broadcast has already
 *    flowed through handleMessage before the ACK — so by the time we
 *    receive it, our local table reflects every competing request
 *    that was accepted before ours.
 * 4. We apply our own request to the local table using the same rule
 *    every peer applies on remote requests: earliest timestamp per key
 *    wins. If a key is already held by someone else (their stamp < ours),
 *    we're denied for that key; otherwise we win.
 * 5. Every peer reaches the same table state because they all apply
 *    frames in the same total order.
 *
 * The module is a tab-local singleton: each browser tab has its own
 * arbitrator, rebuilt from scratch when the relay reconnects. Cross-tab
 * state survives on the relay's broadcast log, not here.
 */

export type LockKey = string;

interface LockEntry {
  userId: string;
  timestampMs: number;
}

/**
 * Injection surface — the arbitrator doesn't know about the EncryptedRelay
 * class directly so it stays testable and the import graph stays shallow.
 */
export interface ArbitratorTransport {
  /** Send an encrypted system message and resolve with its server-stamped timestamp. */
  sendWithSettlement: (msg: object) => Promise<number>;
}

export interface LockRequestMessage {
  type: 'oo:lockRequest';
  userId: string;
  keys: LockKey[];
}

export interface LockReleaseMessage {
  type: 'oo:lockRelease';
  userId: string;
  keys: LockKey[];
}

export interface ClaimResult {
  /** Keys we successfully own in the replicated table. */
  granted: LockKey[];
  /**
   * Keys someone else was already holding at our timestamp. If non-empty
   * the caller should NOT proceed with the local mutation — OO will
   * retry the askLock on its own timer.
   */
  denied: LockKey[];
}

export class WordLockArbitrator {
  private table = new Map<LockKey, LockEntry>();

  constructor(private readonly transport: ArbitratorTransport) {}

  /**
   * Apply a remote peer's claim to the table. Called from the relay's
   * incoming-message pump when a non-self `oo:lockRequest` is decrypted.
   * `timestampMs` is the relay-assigned stamp of that frame.
   *
   * Earliest-stamp-per-key wins: if the key is already held, the claim
   * is dropped silently. The claimant will discover its own denial when
   * it applies its own frame at settlement and sees us here first.
   */
  applyRemoteRequest(msg: LockRequestMessage, timestampMs: number): void {
    for (const key of msg.keys) {
      if (!this.table.has(key)) {
        this.table.set(key, { userId: msg.userId, timestampMs });
      }
    }
  }

  /**
   * Apply a remote peer's release. Only the current holder can release
   * a key — stale releases from a peer that was denied the lock in the
   * first place are ignored to keep the table consistent.
   */
  applyRemoteRelease(msg: LockReleaseMessage): void {
    for (const key of msg.keys) {
      const entry = this.table.get(key);
      if (entry && entry.userId === msg.userId) {
        this.table.delete(key);
      }
    }
  }

  /**
   * Claim `keys` for `userId`. Broadcasts the request via the relay,
   * waits for settlement so our view of the table is causally complete,
   * then applies the request locally under the same rule remote peers
   * use.
   */
  async tryClaim(userId: string, keys: LockKey[]): Promise<ClaimResult> {
    if (keys.length === 0) {
      return { granted: [], denied: [] };
    }

    const timestampMs = await this.transport.sendWithSettlement({
      type: 'oo:lockRequest',
      userId,
      keys,
    });

    const granted: LockKey[] = [];
    const denied: LockKey[] = [];

    for (const key of keys) {
      const existing = this.table.get(key);
      if (existing && existing.userId !== userId) {
        // A peer claimed this key earlier in the log order. They win.
        denied.push(key);
        continue;
      }
      // Either unclaimed or already ours — either way we hold it now.
      this.table.set(key, { userId, timestampMs });
      granted.push(key);
    }

    return { granted, denied };
  }

  /**
   * Release `keys` held by `userId`. Applies locally and broadcasts so
   * peers clear the keys from their tables too. Best-effort on the
   * broadcast side — if settlement fails (socket closed, etc.) local
   * state stays correct; on reconnect every tab rebuilds from scratch
   * anyway and OO re-issues fresh askLock on new edits.
   */
  async release(userId: string, keys: LockKey[]): Promise<void> {
    if (keys.length === 0) return;

    for (const key of keys) {
      const entry = this.table.get(key);
      if (entry && entry.userId === userId) {
        this.table.delete(key);
      }
    }

    try {
      await this.transport.sendWithSettlement({
        type: 'oo:lockRelease',
        userId,
        keys,
      });
    } catch {
      // Settlement drop (socket close) — handled by the reconnect path.
    }
  }

  /**
   * Drop every lock held by `userId`. Called when a peer leaves / crashes
   * so their paragraphs become editable again. Local-only; the caller
   * decides whether to broadcast a release on their behalf.
   */
  dropUser(userId: string): void {
    for (const [key, entry] of this.table) {
      if (entry.userId === userId) {
        this.table.delete(key);
      }
    }
  }

  /**
   * Release every key currently held by `userId`. Convenience wrapper
   * for OO's `unLockDocument`, which releases "all my locks" without
   * specifying which. Returns quickly when the user holds nothing.
   */
  async releaseAll(userId: string): Promise<void> {
    const keys: LockKey[] = [];
    for (const [key, entry] of this.table) {
      if (entry.userId === userId) keys.push(key);
    }
    await this.release(userId, keys);
  }

  /** Reset the table. Called on relay reconnect. */
  reset(): void {
    this.table.clear();
  }

  /** For diagnostics / tests. */
  snapshot(): Array<{ key: LockKey; userId: string; timestampMs: number }> {
    return Array.from(this.table.entries()).map(([key, entry]) => ({
      key,
      userId: entry.userId,
      timestampMs: entry.timestampMs,
    }));
  }
}
