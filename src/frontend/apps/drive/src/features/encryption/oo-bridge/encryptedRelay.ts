/**
 * Encrypted WebSocket relay client for OnlyOffice collaboration.
 *
 * Sits between the OOEditor bridge and the relay server. Encrypts all
 * outgoing OT patches via the vault before sending, and decrypts all
 * incoming patches before passing to OnlyOffice.
 *
 * System messages (JSON text) are NOT encrypted — they contain
 * metadata like peer joins/leaves, locks, and cursor positions.
 */

import type { OOChange } from './types';

const RELAY_URL = process.env.NEXT_PUBLIC_RELAY_URL ?? 'ws://localhost:4100';

// --- System message types (discriminated union) ---

/** Server sends the initial room state when a client joins */
type RoomStateMessage = {
  type: 'room:state';
  peers: Array<{ userId: string; userName: string }>;
  historyLength: number;
};

/** A peer joined the room (broadcast by server after auth) */
type PeerJoinMessage = {
  type: 'peer:join';
  userId: string;
  userName: string;
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
  | SaveUnlockMessage;

export interface RelayCallbacks {
  /** Called when a remote peer's changes arrive (decrypted) */
  onRemoteChanges: (changes: OOChange[]) => void;
  /** Called when a peer joins the room */
  onPeerJoin: (userId: string, userName: string) => void;
  /** Called when a peer leaves the room */
  onPeerLeave: (userId: string) => void;
  /** Called when room state is received (initial peer list) */
  onRoomState: (peers: Array<{ userId: string; userName: string }>) => void;
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

    const url = `${RELAY_URL}?room=${this.roomId}`;
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

  /** Send encrypted OT patches to all peers */
  async sendChanges(changes: OOChange[]): Promise<void> {
    const data = JSON.stringify(changes);
    const encoder = new TextEncoder();
    const plaintext = encoder.encode(data).buffer;

    try {
      const { encryptedData } = await this.vaultClient.encryptWithKey(
        plaintext,
        this.encryptedSymmetricKey,
        this.encryptedKeyChain.length > 0 ? this.encryptedKeyChain : undefined
      );

      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(encryptedData);
      } else {
        // Queue for when we reconnect
        this.pendingOutgoing.push(encryptedData);
      }
    } catch (err) {
      console.error('[relay] Failed to encrypt changes:', err);
    }
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
    await this.sendEncryptedSystem({ type: 'cursor:update', cursor });
  }

  /** Acquire or release the save lock (not encrypted — no sensitive content) */
  sendSaveLock(locked: boolean): void {
    this.sendSystem({
      type: locked ? 'save:lock' : 'save:unlock',
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

  private sendSystem(msg: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  /** Encrypt a system message and send as binary frame */
  private async sendEncryptedSystem(msg: object): Promise<void> {
    const plaintext = new TextEncoder().encode(JSON.stringify(msg)).buffer;

    try {
      const { encryptedData } = await this.vaultClient.encryptWithKey(
        plaintext,
        this.encryptedSymmetricKey,
        this.encryptedKeyChain.length > 0 ? this.encryptedKeyChain : undefined,
      );

      if (this.ws?.readyState === WebSocket.OPEN) {
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

    // Binary frame (Blob) = encrypted data (OT patch or system message)
    if (data instanceof Blob) {
      try {
        const buffer = await data.arrayBuffer();
        const { data: plaintext } = await this.vaultClient.decryptWithKey(
          buffer,
          this.encryptedSymmetricKey,
          this.encryptedKeyChain.length > 0 ? this.encryptedKeyChain : undefined,
        );

        const json = new TextDecoder().decode(plaintext);
        const parsed = JSON.parse(json);

        // Check if it's an encrypted system message (has a "type" field)
        if (parsed.type && typeof parsed.type === 'string') {
          this.handleSystemMessage(parsed as SystemMessage);
        } else if (Array.isArray(parsed)) {
          // Array of OOChange objects
          this.callbacks.onRemoteChanges(parsed as OOChange[]);
        }
      } catch (err) {
        console.error('[relay] Failed to decrypt incoming data:', err);
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
        this.callbacks.onPeerJoin(msg.userId, msg.userName);
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
