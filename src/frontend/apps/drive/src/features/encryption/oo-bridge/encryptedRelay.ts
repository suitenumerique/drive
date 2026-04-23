/**
 * Encrypted WebSocket relay client for OnlyOffice collaboration.
 *
 * Forwards every cross-peer message as an encrypted, opaque envelope. The
 * server never sees plaintext content. System messages from the relay server
 * itself (room state, peer join/leave) come over text frames unencrypted.
 */

const RELAY_URL = process.env.NEXT_PUBLIC_RELAY_URL ?? 'ws://localhost:4100';

// --- System message types (discriminated union) ---

/** Server sends the initial room state when a client joins */
type RoomStateMessage = {
  type: 'room:state';
  peers: Array<{
    userId: string;
    userName: string;
    canEdit: boolean;
    joinedAt: number;
    /** True if this peer has broadcast `peer:crashed`. */
    crashed?: boolean;
  }>;
  historyLength: number;
};

/** A peer joined the room (broadcast by server after auth) */
type PeerJoinMessage = {
  type: 'peer:join';
  userId: string;
  userName: string;
  canEdit: boolean;
  joinedAt: number;
  /** Fresh connections are always false; kept for schema symmetry. */
  crashed?: boolean;
};

/** A peer left the room */
type PeerLeaveMessage = {
  type: 'peer:leave';
  userId: string;
};

/** A cell/range lock was acquired (spreadsheets) */
type LockAcquireMessage = {
  type: 'lock:acquire';
  userId: string;
  lockData: unknown;
};

/** A cell/range lock was released */
type LockReleaseMessage = {
  type: 'lock:release';
  userId: string;
  lockData: unknown;
};

/** A cursor position update from a peer */
type CursorUpdateMessage = {
  type: 'cursor:update';
  userId: string;
  cursor: unknown;
};

/** A peer acquired the save lock (checkpointing in progress) */
type SaveLockMessage = {
  type: 'save:lock';
  userId: string;
};

/** A peer released the save lock */
type SaveUnlockMessage = {
  type: 'save:unlock';
  userId: string;
};

/** Server confirms authentication */
type AuthenticatedMessage = {
  type: 'system:authenticated';
  userId: string;
  userName: string;
  /** Relay-assigned connection timestamp, used as leader-election tiebreaker. */
  joinedAt: number;
};

/** Server signals the end of the history replay burst */
type HistoryEndMessage = {
  type: 'history:end';
};

/** A chat / comment-event message from a peer (OO `message` channel) */
type MessageBroadcastMessage = {
  type: 'oo:message';
  userId: string;
  messages: unknown[];
};

/** A document meta event from a peer (OO `meta` channel — comment locks etc.) */
type MetaBroadcastMessage = {
  type: 'oo:meta';
  userId: string;
  messages: unknown[];
};

/** A complete OO `saveChanges` envelope captured verbatim from the sender */
type SaveChangesBroadcastMessage = {
  type: 'oo:saveChanges';
  userId: string;
  message: Record<string, unknown>;
  /** Optional inline media (image name → data URL) referenced by the change. */
  media?: Record<string, string>;
};

/** The leader persisted a checkpoint to S3 at the given epoch. */
type SaveCommittedMessage = {
  type: 'save:committed';
  epochMs: number;
  userId: string;
};

/**
 * A peer recovering from a local crash wants the save-leader to
 * persist so it can reload against a fresh snapshot epoch. Rate-
 * limited by the relay (one per room per 2s).
 */
type PeerNeedsSaveMessage = {
  type: 'peer:needs-save';
  userId: string;
};

/**
 * A peer's local OO editor has entered an unrecoverable state and is
 * showing the crash overlay. The peer stays connected (so it can still
 * observe `save:committed` for its recovery wait), but surviving peers
 * must exclude it from leader election — a crashed editor can't run
 * `forceSave`, so leaving it as leader deadlocks the room.
 */
type PeerCrashedMessage = {
  type: 'peer:crashed';
  userId: string;
};

/** All possible system messages */
/**
 * Relay's ack that a binary frame we sent has been stamped and queued to
 * every peer. `timestampMs` is the server-authoritative total-order id
 * the relay assigned. Callers awaiting this learn their own position in
 * the log and can safely apply their frame to replicated state.
 */
type FrameSettledMessage = {
  type: 'frame:settled';
  timestampMs: number;
};

/** Word lock-arbitration request broadcast by a peer (encrypted payload). */
type WordLockRequestMessage = {
  type: 'oo:lockRequest';
  userId: string;
  keys: string[];
};

/** Word lock-arbitration release broadcast by a peer (encrypted payload). */
type WordLockReleaseMessage = {
  type: 'oo:lockRelease';
  userId: string;
  keys: string[];
};

type SystemMessage =
  | AuthenticatedMessage
  | HistoryEndMessage
  | RoomStateMessage
  | PeerJoinMessage
  | PeerLeaveMessage
  | LockAcquireMessage
  | LockReleaseMessage
  | CursorUpdateMessage
  | SaveLockMessage
  | SaveUnlockMessage
  | MessageBroadcastMessage
  | MetaBroadcastMessage
  | SaveChangesBroadcastMessage
  | SaveCommittedMessage
  | PeerNeedsSaveMessage
  | PeerCrashedMessage
  | FrameSettledMessage
  | WordLockRequestMessage
  | WordLockReleaseMessage;

export interface RelayCallbacks {
  /** Called when a remote peer's saveChanges envelope arrives (full message) */
  onSaveChanges: (
    userId: string,
    message: Record<string, unknown>,
    media?: Record<string, string>
  ) => void;
  /** Called when a peer joins the room */
  onPeerJoin: (
    userId: string,
    userName: string,
    canEdit: boolean,
    joinedAt: number,
  ) => void;
  /** Called when a peer leaves the room */
  onPeerLeave: (userId: string) => void;
  /** Called when room state is received (initial peer list) */
  onRoomState: (
    peers: Array<{
      userId: string;
      userName: string;
      canEdit: boolean;
      joinedAt: number;
      crashed?: boolean;
    }>,
  ) => void;
  /** Called when a lock is acquired/released by a peer */
  onLockUpdate: (
    type: 'acquire' | 'release',
    userId: string,
    lockData: unknown
  ) => void;
  /** Called when a cursor position update arrives from a peer */
  onCursorUpdate: (userId: string, cursor: unknown) => void;
  /** Called when save lock status changes */
  onSaveLock: (userId: string, locked: boolean) => void;
  /** Called when a peer broadcasts an OO `message` payload (chat, comments) */
  onMessageBroadcast: (userId: string, messages: unknown[]) => void;
  /** Called when a peer broadcasts an OO `meta` payload (comment locks etc.) */
  onMetaBroadcast: (userId: string, messages: unknown[]) => void;
  /** Called on connection status change */
  onConnectionChange: (connected: boolean) => void;
  /** Called when max reconnection attempts are exhausted */
  onReconnectFailed: () => void;
  /**
   * Called when the relay rejects our connection with close code 4001
   * because our `sinceTimestampMs` cursor is older than the relay's
   * purge floor. The editor must refetch the S3 snapshot and reinit —
   * we cannot bring the in-memory OO state up to date from the relay
   * alone.
   */
  onStaleHistory?: () => void;
  /**
   * Called once the relay has finished replaying the room history that
   * predates our join. Fires exactly once per WS connection, after the
   * last history frame and before any live broadcast.
   */
  onHistoryEnd?: () => void;
  /**
   * Called when a remote peer persists a checkpoint to S3. The local
   * editor should clear its "unsaved changes" marker so the
   * beforeunload guard doesn't prompt on close.
   */
  onRemoteSaveCommitted?: (epochMs: number, userId: string) => void;
  /**
   * Called when a remote peer requests the save-leader to persist
   * immediately (used by crash-reload recovery). Only the save-leader
   * should actually save; others ignore it.
   */
  onPeerNeedsSave?: (userId: string) => void;
  /**
   * Called when a remote peer broadcasts `peer:crashed`. The local
   * editor must exclude that userId from leader election until it
   * disconnects or reconnects fresh.
   */
  onPeerCrashed?: (userId: string) => void;
  /**
   * Called when a remote peer's Word-lock request arrives. `timestampMs`
   * is the relay-assigned total-order stamp; the arbitrator applies
   * competing requests by earliest stamp. Only invoked for binary
   * frames (which carry a timestamp) — never fires during history
   * replay: the arbitrator rebuilds from scratch on reconnect so
   * replaying stale locks would poison local state.
   */
  onWordLockRequest?: (
    userId: string,
    keys: string[],
    timestampMs: number,
  ) => void;
  /**
   * Called when a remote peer's Word-lock release arrives. No timestamp
   * needed — releases are idempotent and only affect keys the releasing
   * peer still holds.
   */
  onWordLockRelease?: (userId: string, keys: string[]) => void;
}

export class EncryptedRelay {
  private ws: WebSocket | null = null;
  private roomId: string;
  private userId: string;
  private userName: string;
  private vaultClient: any;
  private encryptedSymmetricKey: ArrayBuffer;
  private encryptedKeyChain: ArrayBuffer[];
  private callbacks: RelayCallbacks;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private destroyed = false;
  private pendingOutgoing: ArrayBuffer[] = [];
  /**
   * Snapshot epoch (client UTC ms) baked into the S3 file this peer just
   * loaded. The relay replays events strictly newer than this so we don't
   * double-apply changes already in the snapshot. Updated after every
   * successful local save.
   */
  private sinceTimestampMs: number;
  /**
   * The `joinedAt` timestamp the relay assigned when it accepted our
   * connection. Populated by the `system:authenticated` frame. Used by
   * the caller as a leader-election tiebreaker when multiple peers
   * share a userId.
   */
  public joinedAt: number | null = null;
  /**
   * Serializes message handling so async binary decrypts can't be overtaken
   * by synchronous text frames that arrived after them on the wire. Without
   * this, `history:end` (text, sync) resolves before the binary history
   * frames that preceded it finish decrypting, and the preload gate closes
   * before the replayed changes land in `historyInitialChanges`.
   */
  private processing: Promise<void> = Promise.resolve();
  /**
   * True until the relay sends `history:end`. While in this phase every
   * incoming frame is a replay from the server's `room.history`, which
   * may contain ephemeral events (cursors, locks) from peers that no
   * longer exist and/or that reference internal OO object IDs from a
   * different ID namespace than ours. Applying them crashes OO, so we
   * drop ephemeral types during history replay and keep only the real
   * document edits.
   */
  private inHistoryPhase = true;

  /**
   * FIFO queue of pending-send resolvers. Each encrypted binary frame
   * we submit to the relay adds one entry here, and every `frame:settled`
   * system message from the relay resolves the head entry. Relies on two
   * facts to stay in sync: (a) the relay processes our incoming binary
   * frames in the order we submitted them (single socket, single event
   * loop on the server), and (b) it emits settlements in that same order.
   * If a send fails before submission (network error), we reject the
   * resolver locally to avoid leaking entries.
   */
  private settlementQueue: Array<{
    resolve: (timestampMs: number) => void;
    reject: (err: unknown) => void;
  }> = [];

  constructor(opts: {
    roomId: string;
    userId: string;
    userName: string;
    vaultClient: any;
    encryptedSymmetricKey: ArrayBuffer;
    encryptedKeyChain: ArrayBuffer[];
    callbacks: RelayCallbacks;
    /** Snapshot epoch (ms) from S3 metadata; 0 means no snapshot. */
    sinceTimestampMs?: number;
  }) {
    this.roomId = opts.roomId;
    this.userId = opts.userId;
    this.userName = opts.userName;
    this.vaultClient = opts.vaultClient;
    this.encryptedSymmetricKey = opts.encryptedSymmetricKey;
    this.encryptedKeyChain = opts.encryptedKeyChain;
    this.callbacks = opts.callbacks;
    this.sinceTimestampMs = opts.sinceTimestampMs ?? 0;
  }

  /** Connect to the relay server */
  connect(): void {
    if (this.destroyed) return;
    // Every (re)connect starts with a history replay burst.
    this.inHistoryPhase = true;

    const params = new URLSearchParams({ room: this.roomId });
    if (this.sinceTimestampMs > 0) {
      params.set('since', String(this.sinceTimestampMs));
    }
    const url = `${RELAY_URL}?${params.toString()}`;
    console.warn(
      `[relay] connecting since=${this.sinceTimestampMs} url=${url}`,
    );
    this.ws = new WebSocket(url);
    // Don't set binaryType to 'arraybuffer' — we need to distinguish
    // text frames (JSON system messages) from binary frames (encrypted patches).
    // Text frames arrive as string, binary frames as Blob.

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.callbacks.onConnectionChange(true);

      // No need to send peer:join — the server authenticates via cookies
      // and announces our identity to other peers automatically.

      // Flush pending outgoing messages
      for (const msg of this.pendingOutgoing) {
        this.ws?.send(msg);
      }
      this.pendingOutgoing = [];
    };

    this.ws.onmessage = event => {
      const data = event.data;
      this.processing = this.processing.then(() => this.handleMessage(data));
    };

    this.ws.onclose = event => {
      this.callbacks.onConnectionChange(false);
      // Pending settlement promises become unresolvable once the socket
      // is gone — the relay on the other side of a future reconnect
      // won't know about frames we sent on this connection. Reject them
      // now so callers (lock arbitrator, etc.) can decide to retry or
      // fail fast.
      this.drainSettlementQueue('connection closed');
      // 4001 = stale history. The relay cannot serve us the events we
      // missed; the editor needs to fully reinit from S3. Do NOT
      // reconnect — just surface the condition and stop.
      if (event.code === 4001) {
        console.warn('[relay] closed with stale-history (4001)');
        this.destroyed = true;
        this.callbacks.onStaleHistory?.();
        return;
      }
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      // onclose will be called after onerror
    };
  }

  /**
   * Newly-inserted images (name → data URL) waiting to be shipped with the
   * next saveChanges. Drained when the change goes out so that peers receive
   * the bytes in the same envelope as the change that references them.
   */
  private pendingMedia: Record<string, string> = {};

  /** Stash an image to broadcast with the next saveChanges envelope. */
  queuePendingMedia(name: string, dataUrl: string): void {
    this.pendingMedia[name] = dataUrl;
  }

  /** Broadcast a full OO `saveChanges` envelope to all peers (encrypted) */
  async sendSaveChanges(message: Record<string, unknown>): Promise<void> {
    const media = Object.keys(this.pendingMedia).length
      ? this.pendingMedia
      : undefined;
    this.pendingMedia = {};
    await this.sendEncryptedSystem({
      type: 'oo:saveChanges',
      userId: this.userId,
      message,
      media,
    });
  }

  /** Send a lock request to all peers (encrypted — lock data is sensitive) */
  async sendLock(
    type: 'acquire' | 'release',
    lockData: unknown
  ): Promise<void> {
    await this.sendEncryptedSystem({
      type: type === 'acquire' ? 'lock:acquire' : 'lock:release',
      lockData,
    });
  }

  /** Send cursor position to all peers (encrypted — position is sensitive) */
  async sendCursor(cursor: unknown): Promise<void> {
    await this.sendEncryptedSystem({
      type: 'cursor:update',
      userId: this.userId,
      cursor,
    });
  }

  /** Broadcast an OO `message` payload (chat or comment events) */
  async sendMessage(messages: unknown[]): Promise<void> {
    await this.sendEncryptedSystem({
      type: 'oo:message',
      userId: this.userId,
      messages,
    });
  }

  /** Broadcast an OO `meta` payload (comment locks, etc.) */
  async sendMeta(messages: unknown[]): Promise<void> {
    await this.sendEncryptedSystem({
      type: 'oo:meta',
      userId: this.userId,
      messages,
    });
  }

  /** Acquire or release the save lock (not encrypted — no sensitive content) */
  sendSaveLock(locked: boolean): void {
    this.sendSystem({
      type: locked ? 'save:lock' : 'save:unlock',
    });
  }

  /**
   * Notify the relay that a fresh S3 snapshot has been committed with the
   * given epoch (client UTC ms). The relay schedules a delayed purge of
   * every history entry whose timestamp is <= epochMs.
   */
  sendSaveCommitted(epochMs: number): void {
    if (epochMs > this.sinceTimestampMs) {
      this.sinceTimestampMs = epochMs;
    }
    this.sendSystem({ type: 'save:committed', epochMs });
  }

  /**
   * Advance the local replay cursor WITHOUT sending anything to the
   * relay. Used when we observe a remote peer's `save:committed` — we
   * want our reconnect `?since=` to reflect that epoch, but we must
   * not re-broadcast or the relay would rebroadcast it back to us.
   */
  observeRemoteSaveCommitted(epochMs: number): void {
    if (epochMs > this.sinceTimestampMs) {
      this.sinceTimestampMs = epochMs;
    }
  }

  /**
   * Ask the save-leader in the room to persist immediately. Used by
   * the crash-recovery reload path so the reinit can pick up a fresh
   * snapshot epoch. The relay rate-limits rebroadcasts (one per room
   * per 2s), and the leader-side handler respects the existing
   * `isSaving` guard, so callers don't need to debounce.
   */
  sendNeedsSave(): void {
    this.sendSystem({ type: 'peer:needs-save' });
  }

  sendCrashed(): void {
    this.sendSystem({ type: 'peer:crashed' });
  }

  /** Disconnect and clean up */
  destroy(): void {
    this.destroyed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null; // prevent reconnect
      this.ws.close();
      this.ws = null;
    }
  }

  /** Check if connected */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // --- Private ---

  /**
   * The vault worker takes ownership of every ArrayBuffer it receives via
   * postMessage (transfer list), detaching the original. Our key material is
   * long-lived and used across many encrypt/decrypt calls, so we hand the
   * worker a FRESH copy each time — otherwise the first save() in the
   * session detaches the key and every subsequent decrypt fails with
   * "wrong secret key for the given ciphertext".
   */
  private cloneKey(): ArrayBuffer {
    return this.encryptedSymmetricKey.slice(0);
  }

  private cloneKeyChain(): ArrayBuffer[] | undefined {
    if (this.encryptedKeyChain.length === 0) return undefined;
    return this.encryptedKeyChain.map(k => k.slice(0));
  }

  private sendSystem(msg: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify(msg);
      console.log(
        '[relay] send TEXT',
        (msg as { type?: string }).type ?? '?',
        'size:',
        payload.length
      );
      this.ws.send(payload);
    }
  }

  /**
   * Like `sendEncryptedSystem` but returns a Promise that resolves once
   * the relay has stamped, broadcast, and ACKed our frame. Callers use
   * this to order concurrent replicated-state mutations (lock requests,
   * lock releases). The resolved `timestampMs` is our frame's position
   * in the total order the relay maintains for this room.
   *
   * By the time the promise resolves, TCP FIFO guarantees every earlier
   * frame broadcast by the relay to us has already passed through
   * `handleMessage` — so local replicated state is causally complete up
   * to (but not including) our frame, and we can safely apply our own
   * frame on top.
   */
  async sendEncryptedWithSettlement(msg: object): Promise<number> {
    return new Promise<number>((resolve, reject) => {
      // Register the resolver BEFORE dispatch so a settlement that
      // arrives on the next microtask still finds its slot in the queue.
      const pending = { resolve, reject };
      this.settlementQueue.push(pending);
      void this.sendEncryptedBinary(msg).then(delivered => {
        if (!delivered) {
          // Encryption threw, or the socket was closed before we could
          // send. The relay will not emit a settlement for this frame;
          // drop our slot to keep the FIFO aligned with future sends.
          const idx = this.settlementQueue.indexOf(pending);
          if (idx >= 0) this.settlementQueue.splice(idx, 1);
          reject(new Error('Encrypted frame was not delivered to relay'));
        }
      });
    });
  }

  /**
   * Reject every pending settlement resolver. Called on socket close to
   * unblock callers awaiting a settlement that will never come.
   */
  private drainSettlementQueue(reason: string): void {
    if (this.settlementQueue.length === 0) return;
    const err = new Error(`Settlement dropped: ${reason}`);
    const pending = this.settlementQueue.splice(0);
    for (const p of pending) {
      p.reject(err);
    }
  }

  /** Encrypt a system message and send as binary frame (fire-and-forget). */
  private async sendEncryptedSystem(msg: object): Promise<void> {
    await this.sendEncryptedBinary(msg);
  }

  /**
   * Encrypt `msg` and submit it as a binary frame to the relay. Returns
   * `true` iff the frame was actually written to the socket — callers
   * awaiting settlement can use this to decide whether to expect a
   * `frame:settled` back. Errors are logged and swallowed to match the
   * original fire-and-forget contract.
   */
  private async sendEncryptedBinary(msg: object): Promise<boolean> {
    const type = (msg as { type?: string }).type ?? '?';
    const plaintext = new TextEncoder().encode(JSON.stringify(msg)).buffer;
    const plaintextSize = plaintext.byteLength;

    try {
      const chain = this.cloneKeyChain();
      const { encryptedData } = chain
        ? await this.vaultClient.encryptWithKey(
            plaintext,
            this.cloneKey(),
            chain
          )
        : await this.vaultClient.encryptWithKey(plaintext, this.cloneKey());

      if (this.ws?.readyState !== WebSocket.OPEN) {
        return false;
      }
      const head = new Uint8Array(
        encryptedData.slice(0, Math.min(16, encryptedData.byteLength))
      );
      const headHex = Array.from(head)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
      console.log(
        '[relay] send',
        type,
        'plaintext:',
        plaintextSize,
        'cipher:',
        encryptedData.byteLength,
        'head:',
        headHex
      );
      this.ws.send(encryptedData);
      return true;
    } catch (err) {
      console.error('[relay] Failed to encrypt system message:', err);
      return false;
    }
  }

  private async handleMessage(data: unknown): Promise<void> {
    // Text frame = JSON system message (not encrypted)
    if (typeof data === 'string') {
      try {
        const msg = JSON.parse(data) as SystemMessage;
        this.handleSystemMessage(msg);
      } catch {
        // Not valid JSON
      }
      return;
    }

    // Binary frame (Blob or ArrayBuffer) = encrypted data (OT patch or system message)
    let buffer: ArrayBuffer | null = null;
    if (data instanceof Blob) {
      buffer = await data.arrayBuffer();
    } else if (data instanceof ArrayBuffer) {
      buffer = data;
    }

    if (buffer) {
      // Every binary frame from the relay is prefixed with an 8-byte
      // big-endian u64 timestampMs assigned server-side. Strip it before
      // decryption and use it to advance our `sinceTimestampMs` cursor
      // so reconnects skip anything we've already seen.
      if (buffer.byteLength < 8 + 32) {
        return;
      }
      const view = new DataView(buffer);
      const timestampMs = Number(view.getBigUint64(0, false));
      const ciphertext = buffer.slice(8);

      // Capture a fingerprint of the incoming frame BEFORE we hand the
      // buffer to the vault worker (which transfers ownership, detaching
      // the original). This lets us log size + leading bytes on failure.
      const head = new Uint8Array(
        ciphertext.slice(0, Math.min(16, ciphertext.byteLength))
      );
      const headHex = Array.from(head)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
      const size = ciphertext.byteLength;

      try {
        const { data: plaintext } = await this.vaultClient.decryptWithKey(
          ciphertext,
          this.cloneKey(),
          this.cloneKeyChain()
        );

        const json = new TextDecoder().decode(plaintext);
        const parsed = JSON.parse(json);

        if (parsed.type && typeof parsed.type === 'string') {
          this.handleSystemMessage(parsed as SystemMessage, timestampMs);
          // Advance the cursor only after successful decrypt+dispatch so
          // a bad frame doesn't skip us past good ones on reconnect.
          if (timestampMs > this.sinceTimestampMs) {
            this.sinceTimestampMs = timestampMs;
          }
        }
      } catch (err) {
        console.warn(
          '[relay] decrypt failed — size:',
          size,
          'head:',
          headHex,
          'err:',
          err
        );
      }
    }
  }

  private handleSystemMessage(
    msg: SystemMessage,
    timestampMs?: number,
  ): void {
    // Drop ephemeral/live-state events during history replay. These
    // reference in-memory object ids (Run handles, block guids) that
    // were valid at the moment the sender emitted them but may have
    // been removed or replaced by later saveChanges in the history.
    // Replaying them makes OO look up a no-longer-existing object and
    // crash in handlers like `Update_ForeignCursor`
    // (`Run.GetDocumentPositionFromObject is not a function`) or
    // `onLocksAcquired` (`Set_UserId on undefined`). `saveChanges` is
    // the only safe type: it carries its own OT anchoring and is what
    // rebuilds the doc state we need anyway.
    if (
      this.inHistoryPhase &&
      (msg.type === 'lock:acquire' ||
        msg.type === 'lock:release' ||
        msg.type === 'oo:lockRequest' ||
        msg.type === 'oo:lockRelease' ||
        msg.type === 'cursor:update' ||
        msg.type === 'save:lock' ||
        msg.type === 'save:unlock')
    ) {
      return;
    }
    switch (msg.type) {
      case 'frame:settled':
        // Relay has stamped and enqueued the next pending send. TCP FIFO
        // on our socket guarantees every frame with a smaller timestamp
        // we need to know about has already been delivered to us above
        // this message. Resolve the head of the queue so the caller can
        // safely apply its frame to local replicated state.
        if (typeof msg.timestampMs === 'number') {
          const pending = this.settlementQueue.shift();
          pending?.resolve(msg.timestampMs);
        }
        break;
      case 'system:authenticated':
        // Auth confirmed; record our relay-assigned `joinedAt` so the
        // editor can use it as a leader-election tiebreaker.
        if (typeof msg.joinedAt === 'number') {
          this.joinedAt = msg.joinedAt;
        }
        break;
      case 'history:end':
        this.inHistoryPhase = false;
        this.callbacks.onHistoryEnd?.();
        break;
      case 'room:state':
        this.callbacks.onRoomState(msg.peers);
        break;
      case 'peer:join':
        this.callbacks.onPeerJoin(
          msg.userId,
          msg.userName,
          msg.canEdit,
          msg.joinedAt,
        );
        break;
      case 'peer:leave':
        this.callbacks.onPeerLeave(msg.userId);
        break;
      case 'lock:acquire':
        this.callbacks.onLockUpdate('acquire', msg.userId, msg.lockData);
        break;
      case 'lock:release':
        this.callbacks.onLockUpdate('release', msg.userId, msg.lockData);
        break;
      case 'cursor:update':
        this.callbacks.onCursorUpdate(msg.userId, msg.cursor);
        break;
      case 'save:lock':
        this.callbacks.onSaveLock(msg.userId, true);
        break;
      case 'save:unlock':
        this.callbacks.onSaveLock(msg.userId, false);
        break;
      case 'oo:message':
        this.callbacks.onMessageBroadcast(msg.userId, msg.messages);
        break;
      case 'oo:meta':
        this.callbacks.onMetaBroadcast(msg.userId, msg.messages);
        break;
      case 'oo:saveChanges':
        this.callbacks.onSaveChanges(msg.userId, msg.message, msg.media);
        break;
      case 'save:committed':
        this.callbacks.onRemoteSaveCommitted?.(msg.epochMs, msg.userId);
        break;
      case 'peer:needs-save':
        this.callbacks.onPeerNeedsSave?.(msg.userId);
        break;
      case 'peer:crashed':
        this.callbacks.onPeerCrashed?.(msg.userId);
        break;
      case 'oo:lockRequest':
        // Word lock-arbitration frame. Carries a timestamp because it
        // arrived as a binary frame; skip if somehow received via a
        // text frame (should never happen given the encrypted delivery
        // path, but the type system allows it).
        if (typeof timestampMs === 'number') {
          this.callbacks.onWordLockRequest?.(
            msg.userId,
            msg.keys,
            timestampMs,
          );
        }
        break;
      case 'oo:lockRelease':
        this.callbacks.onWordLockRelease?.(msg.userId, msg.keys);
        break;
    }
  }

  private scheduleReconnect(): void {
    if (this.destroyed) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn(
        '[relay] Max reconnection attempts reached, retrying every 60s'
      );
      this.callbacks.onReconnectFailed();
      // Keep trying every 60s in the background — the server may come back
      this.reconnectTimer = setTimeout(() => {
        this.reconnectAttempts = 0;
        this.connect();
      }, 60_000);
      return;
    }

    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30_000);
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }
}
