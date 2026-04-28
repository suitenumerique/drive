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

/**
 * The leader persisted a fresh rendered archive to S3. Used purely as a
 * signal for peers to clear their "unsaved changes" beforeunload guard.
 * ID alignment is handled peer-to-peer via `oo:state-response` /
 * `oo:checkpoint-reload`, not via S3.
 */
type SaveCommittedMessage = {
  type: 'save:committed';
  userId: string;
};

/**
 * A peer recovering from a local crash wants the save-leader to
 * persist so it can cold-reload from a fresh S3 snapshot. Rate-limited
 * by the relay (one per room per 2s).
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

/**
 * Lock-arbitration request broadcast by a peer (encrypted payload).
 * `keys` are opaque to the relay — Word uses paragraph ids, Calc /
 * Slide use `block.guid`. `blocks` is a parallel array carrying the
 * verbatim OO descriptor for each key, present for cell / slide so
 * the receiver can hand the full shape to OO (Calc reads
 * `block.sheetId.indexOf` etc — a bare `{ guid }` reply crashes).
 */
type ArbitratedLockRequestMessage = {
  type: 'oo:lockRequest';
  userId: string;
  keys: string[];
  blocks?: unknown[];
};

/** Lock-arbitration release broadcast by a peer (encrypted payload). */
type ArbitratedLockReleaseMessage = {
  type: 'oo:lockRelease';
  userId: string;
  keys: string[];
};

/**
 * A joiner asks for the current live state. Broadcast unencrypted
 * (pure text frame) so every peer can see the request. Only the leader
 * actually answers with a matching `oo:state-response` (encrypted).
 */
type PeerStateRequestMessage = {
  type: 'peer:state-request';
  userId: string;
};

/**
 * The leader's response to a `peer:state-request`. Carries the full
 * live state: the leader's current baseBin (the native-bin string OO
 * was loaded from, or from the last checkpoint) plus every saveChanges
 * observed since. The joiner loads baseBin + replays chain → their
 * OO ends up identical to the leader's, including every internal id.
 */
type PeerStateResponseMessage = {
  type: 'oo:state-response';
  /** Target joiner userId — other peers ignore when they see it. */
  targetUserId: string;
  /** From-userId (leader). */
  userId: string;
  /** Native-bin string, format `"DOCY;v5;{size};{base64data}"`. */
  baseBin: string;
  /** Ordered saveChanges messages (opaque OO envelopes) since baseBin. */
  chain: Array<Record<string, unknown>>;
};

/**
 * Leader-initiated full-room reload. Fires when the local chain grows
 * past a size threshold — the leader snapshots fresh state via
 * `asc_nativeGetFile()`, publishes it as the new baseBin, and every
 * peer destroys + recreates its OO iframe with that bin. Resets chain
 * on all sides to zero. This is the only moment that existing peers
 * visibly "flash" — between checkpoints they stay put and keep their
 * in-memory OO running.
 */
type CheckpointReloadMessage = {
  type: 'oo:checkpoint-reload';
  userId: string;
  baseBin: string;
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
  | ArbitratedLockRequestMessage
  | ArbitratedLockReleaseMessage
  | PeerStateRequestMessage
  | PeerStateResponseMessage
  | CheckpointReloadMessage;

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
    joinedAt: number
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
    }>
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
   * Called once the relay has finished the initial connect sequence
   * (auth + room state). Marks the moment we're ready to start
   * participating in live traffic. Fires exactly once per WS
   * connection.
   */
  onHistoryEnd?: () => void;
  /**
   * Called when a remote peer persists a fresh rendered archive to S3.
   * Used purely to clear the local "unsaved changes" beforeunload
   * marker. ID alignment is handled on the separate
   * `oo:checkpoint-reload` channel.
   */
  onRemoteSaveCommitted?: (userId: string) => void;
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
  onArbitratedLockRequest?: (
    userId: string,
    keys: string[],
    timestampMs: number,
    /**
     * Optional parallel array to `keys` carrying the original OO
     * block descriptor. Senders include this for cell / slide so
     * the receiver can hand the verbatim block to OO (Calc /
     * PowerPoint editors crash on minimal `{ guid }` reconstructions
     * when they read `block.sheetId.indexOf` etc). Undefined for
     * Word — the key IS the block (paragraph id string).
     */
    blocks?: unknown[]
  ) => void;
  /**
   * Called when a remote peer's lock release arrives. No timestamp
   * needed — releases are idempotent and only affect keys the releasing
   * peer still holds.
   */
  onArbitratedLockRelease?: (userId: string, keys: string[]) => void;
  /**
   * Called when a joining peer broadcasts `peer:state-request`. On the
   * receive side, the leader answers with its current (baseBin, chain)
   * via `sendStateResponse(...)`. Non-leader peers ignore.
   */
  onPeerStateRequest?: (fromUserId: string) => void;
  /**
   * Called when a state-response arrives that targets us. `baseBin` is
   * the leader's native-bin string; `chain` is the ordered saveChanges
   * messages since that bin. Caller is expected to reinit OO with this
   * state so its internal object ids match the leader's.
   */
  onPeerStateResponse?: (
    fromUserId: string,
    baseBin: string,
    chain: Array<Record<string, unknown>>
  ) => void;
  /**
   * Called on every peer when the leader broadcasts a checkpoint. All
   * peers (including the leader) destroy + recreate their OO iframe
   * from the given baseBin and reset their local chain to empty.
   */
  onCheckpointReload?: (fromUserId: string, baseBin: string) => void;
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
  /**
   * The `joinedAt` timestamp the relay assigned when it accepted our
   * connection. Populated by the `system:authenticated` frame. Used by
   * the caller as a leader-election tiebreaker when multiple peers
   * share a userId.
   */
  public joinedAt: number | null = null;
  /**
   * Serializes message handling so async binary decrypts can't be
   * overtaken by synchronous text frames that arrived after them on
   * the wire.
   */
  private processing: Promise<void> = Promise.resolve();
  /**
   * True until the relay sends `history:end` (no actual history is
   * sent anymore, but the marker still fires once post-auth to
   * signal "connect handshake complete"). Used to gate early binary
   * frames that arrive before OO is ready for them.
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
  }) {
    this.roomId = opts.roomId;
    this.userId = opts.userId;
    this.userName = opts.userName;
    this.vaultClient = opts.vaultClient;
    this.encryptedSymmetricKey = opts.encryptedSymmetricKey;
    this.encryptedKeyChain = opts.encryptedKeyChain;
    this.callbacks = opts.callbacks;
  }

  /** Connect to the relay server */
  connect(): void {
    if (this.destroyed) return;
    // Every (re)connect starts with a history replay burst.
    this.inHistoryPhase = true;

    const params = new URLSearchParams({ room: this.roomId });
    const url = `${RELAY_URL}?${params.toString()}`;
    console.warn(`[relay] connecting url=${url}`);
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
   * Notify the relay that a fresh rendered archive has been committed
   * to S3. Broadcast to peers so they clear their local "unsaved
   * changes" marker. ID alignment is handled on the peer-to-peer state
   * channel, not via S3.
   */
  sendSaveCommitted(): void {
    this.sendSystem({ type: 'save:committed' });
  }

  /**
   * Ask the save-leader in the room to persist immediately. Used by
   * the crash-recovery reload path so the reinit can cold-load a fresh
   * S3 snapshot. The relay rate-limits rebroadcasts (one per room per
   * 2s), and the leader-side handler respects the existing `isSaving`
   * guard, so callers don't need to debounce.
   */
  sendNeedsSave(): void {
    this.sendSystem({ type: 'peer:needs-save' });
  }

  sendCrashed(): void {
    this.sendSystem({ type: 'peer:crashed' });
  }

  /**
   * Announce to the room that we need someone to ship us their live
   * state. Plain text frame (not encrypted) — peers dispatch to the
   * leader-side `onPeerStateRequest` on receive.
   */
  sendStateRequest(): void {
    this.sendSystem({ type: 'peer:state-request', userId: this.userId });
  }

  /**
   * Leader-only response to a `peer:state-request`. Carries the
   * leader's current baseBin and the chain of saveChanges since.
   * Encrypted binary frame so the payload never leaks to the relay.
   * `targetUserId` is the joiner — other peers that see this frame
   * will still decrypt it (no way to skip: binary frames go to
   * everyone) but their `onPeerStateResponse` handler filters on the
   * target.
   */
  async sendStateResponse(
    targetUserId: string,
    baseBin: string,
    chain: Array<Record<string, unknown>>
  ): Promise<void> {
    await this.sendEncryptedSystem({
      type: 'oo:state-response',
      targetUserId,
      userId: this.userId,
      baseBin,
      chain,
    });
  }

  /**
   * Leader broadcasts a full-room reload with a new baseBin. Every
   * peer (including the leader) destroys + recreates its OO iframe
   * from this bin and resets its chain to empty. Triggered when the
   * local chain grows past a size threshold.
   */
  async sendCheckpointReload(baseBin: string): Promise<void> {
    await this.sendEncryptedSystem({
      type: 'oo:checkpoint-reload',
      userId: this.userId,
      baseBin,
    });
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

  private cloneKey(): ArrayBuffer {
    return this.encryptedSymmetricKey;
  }

  private cloneKeyChain(): ArrayBuffer[] | undefined {
    if (this.encryptedKeyChain.length === 0) return undefined;
    return this.encryptedKeyChain;
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
      // Relay frames are small JSON envelopes (locks, cursors, deltas) — not
      // worth opting into `optimizeMemory`; keep the safe default.
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
      // big-endian u64 timestampMs assigned server-side. Strip it
      // before decryption — the timestamp is the total-order seq used
      // by the lock arbitrator to rank competing requests.
      if (buffer.byteLength < 8 + 32) {
        return;
      }
      const view = new DataView(buffer);
      const timestampMs = Number(view.getBigUint64(0, false));
      const ciphertext = buffer.slice(8);

      // Capture a fingerprint of the incoming frame so failures can log
      // size + leading bytes even after the call.
      const head = new Uint8Array(
        ciphertext.slice(0, Math.min(16, ciphertext.byteLength))
      );
      const headHex = Array.from(head)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
      const size = ciphertext.byteLength;

      try {
        // Relay frames are small JSON envelopes — keep the safe default.
        const { data: plaintext } = await this.vaultClient.decryptWithKey(
          ciphertext,
          this.cloneKey(),
          this.cloneKeyChain()
        );

        const json = new TextDecoder().decode(plaintext);
        const parsed = JSON.parse(json);

        if (parsed.type && typeof parsed.type === 'string') {
          this.handleSystemMessage(parsed as SystemMessage, timestampMs);
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

  private handleSystemMessage(msg: SystemMessage, timestampMs?: number): void {
    // Drop ephemeral/live-state events during history replay. These
    // reference in-memory object ids (cell-lock guids, Run handles)
    // that were valid at the moment the sender emitted them but may
    // have been replaced by later saveChanges in the history or
    // regenerated on the receiver's fresh load.
    //
    // `oo:lockRequest` / `oo:lockRelease` are ALSO dropped: keeping
    // them would correctly rehydrate the arbitrator from history,
    // BUT in practice peers never release (our saveChanges handler
    // doesn't auto-release to avoid OT races, and `unLockDocument`
    // only fires on explicit editor blur / save). A rehydrated
    // arbitrator therefore leaves every paragraph the sender ever
    // touched flagged as held forever — the joiner can't edit any
    // of them until the holder fully leaves. Starting with an empty
    // arbitrator after reload is the lesser evil: the joiner can
    // type immediately, at the risk of a structural-edit collision
    // if both sides race on the same block. Accepted as a tradeoff
    // until we move to ID-preserving persistence (embedded .bin).
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
          msg.joinedAt
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
        this.callbacks.onRemoteSaveCommitted?.(msg.userId);
        break;
      case 'peer:needs-save':
        this.callbacks.onPeerNeedsSave?.(msg.userId);
        break;
      case 'peer:crashed':
        this.callbacks.onPeerCrashed?.(msg.userId);
        break;
      case 'oo:lockRequest':
        // Lock-arbitration frame (Word paragraph id, Calc / Slide
        // GUID — keys are opaque strings to the relay). Carries a
        // timestamp because it arrived as a binary frame; skip if
        // somehow received via a text frame (should never happen
        // given the encrypted delivery path, but the type system
        // allows it).
        if (typeof timestampMs === 'number') {
          this.callbacks.onArbitratedLockRequest?.(
            msg.userId,
            msg.keys,
            timestampMs,
            (msg as { blocks?: unknown[] }).blocks
          );
        }
        break;
      case 'oo:lockRelease':
        this.callbacks.onArbitratedLockRelease?.(msg.userId, msg.keys);
        break;
      case 'peer:state-request':
        // Any peer can receive this; only the leader answers.
        this.callbacks.onPeerStateRequest?.(msg.userId);
        break;
      case 'oo:state-response':
        // Every peer decrypts (binary frames go to everyone), but the
        // handler filters on `targetUserId` so only the joiner acts.
        if (msg.targetUserId === this.userId) {
          this.callbacks.onPeerStateResponse?.(
            msg.userId,
            msg.baseBin,
            msg.chain
          );
        }
        break;
      case 'oo:checkpoint-reload':
        this.callbacks.onCheckpointReload?.(msg.userId, msg.baseBin);
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
