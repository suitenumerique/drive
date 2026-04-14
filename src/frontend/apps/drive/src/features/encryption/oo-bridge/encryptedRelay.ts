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
  peers: Array<{ userId: string; userName: string; canEdit: boolean }>;
  historyLength: number;
};

/** A peer joined the room (broadcast by server after auth) */
type PeerJoinMessage = {
  type: 'peer:join';
  userId: string;
  userName: string;
  canEdit: boolean;
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

/** All possible system messages */
type SystemMessage =
  | AuthenticatedMessage
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
  | SaveChangesBroadcastMessage;

export interface RelayCallbacks {
  /** Called when a remote peer's saveChanges envelope arrives (full message) */
  onSaveChanges: (
    userId: string,
    message: Record<string, unknown>,
    media?: Record<string, string>,
  ) => void;
  /** Called when a peer joins the room */
  onPeerJoin: (userId: string, userName: string, canEdit: boolean) => void;
  /** Called when a peer leaves the room */
  onPeerLeave: (userId: string) => void;
  /** Called when room state is received (initial peer list) */
  onRoomState: (peers: Array<{ userId: string; userName: string; canEdit: boolean }>) => void;
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

    const params = new URLSearchParams({ room: this.roomId });
    if (this.sinceTimestampMs > 0) {
      params.set('since', String(this.sinceTimestampMs));
    }
    const url = `${RELAY_URL}?${params.toString()}`;
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
      this.handleMessage(event.data);
    };

    this.ws.onclose = () => {
      this.callbacks.onConnectionChange(false);
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
  async sendLock(type: 'acquire' | 'release', lockData: unknown): Promise<void> {
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
      this.ws.send(JSON.stringify(msg));
    }
  }

  /** Encrypt a system message and send as binary frame */
  private async sendEncryptedSystem(msg: object): Promise<void> {
    const type = (msg as { type?: string }).type ?? '?';
    const plaintext = new TextEncoder().encode(JSON.stringify(msg)).buffer;
    const plaintextSize = plaintext.byteLength;

    try {
      const { encryptedData } = await this.vaultClient.encryptWithKey(
        plaintext,
        this.cloneKey(),
        this.cloneKeyChain(),
      );

      if (this.ws?.readyState === WebSocket.OPEN) {
        const head = new Uint8Array(
          encryptedData.slice(0, Math.min(16, encryptedData.byteLength)),
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
          headHex,
        );
        this.ws.send(encryptedData);
      }
    } catch (err) {
      console.error('[relay] Failed to encrypt system message:', err);
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
      // Skip tiny frames that can't be valid encrypted content
      // (vault encryption adds at minimum a nonce + auth tag overhead)
      if (buffer.byteLength < 32) {
        return;
      }

      // Capture a fingerprint of the incoming frame BEFORE we hand the
      // buffer to the vault worker (which transfers ownership, detaching
      // the original). This lets us log size + leading bytes on failure.
      const head = new Uint8Array(buffer.slice(0, Math.min(16, buffer.byteLength)));
      const headHex = Array.from(head)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
      const size = buffer.byteLength;

      try {
        const { data: plaintext } = await this.vaultClient.decryptWithKey(
          buffer,
          this.cloneKey(),
          this.cloneKeyChain(),
        );

        const json = new TextDecoder().decode(plaintext);
        const parsed = JSON.parse(json);

        if (parsed.type && typeof parsed.type === 'string') {
          this.handleSystemMessage(parsed as SystemMessage);
        }
      } catch (err) {
        console.warn(
          '[relay] decrypt failed — size:',
          size,
          'head:',
          headHex,
          'err:',
          err,
        );
      }
    }
  }

  private handleSystemMessage(msg: SystemMessage): void {
    switch (msg.type) {
      case 'system:authenticated':
        // Auth confirmed — nothing to do, connection is already established
        break;
      case 'room:state':
        this.callbacks.onRoomState(msg.peers);
        break;
      case 'peer:join':
        this.callbacks.onPeerJoin(msg.userId, msg.userName, msg.canEdit);
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
    }
  }

  private scheduleReconnect(): void {
    if (this.destroyed) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[relay] Max reconnection attempts reached, retrying every 60s');
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
