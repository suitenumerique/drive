/**
 * WebSocket relay server for encrypted OnlyOffice collaboration.
 *
 * Authentication: validates the user's session cookie against the Drive
 * backend API at connection time (like Docs does with HocusPocus).
 * Only users with access to the item can join the room.
 *
 * Zero knowledge: the server only sees encrypted blobs.
 */

import { WebSocketServer, WebSocket, RawData } from 'ws';
import { createServer, IncomingMessage } from 'http';

const PORT = parseInt(process.env.RELAY_PORT || '4100', 10);
const DRIVE_API_URL = process.env.DRIVE_API_URL || 'http://app-dev:8000';
const PING_INTERVAL_MS = 30_000;
// Upper bound on a single relayed message. The frontend caps raw image bytes
// at 50 MB; allow ~75 MB on the wire to absorb base64 (+33%), the JSON change
// envelope and the encryption header. A peer trying to push more is closed
// by ws with code 1009 (Message Too Big).
const MAX_PAYLOAD_BYTES = 75 * 1024 * 1024;

// --- Auth ---

interface AuthResult {
  userId: string;
  userName: string;
  canEdit: boolean;
}

async function authenticateConnection(
  req: IncomingMessage,
  roomId: string
): Promise<AuthResult | null> {
  const cookie = req.headers.cookie || '';
  try {
    const itemUrl = `${DRIVE_API_URL}/api/v1.0/items/${roomId}/`;
    const itemResp = await fetch(itemUrl, {
      headers: {
        Cookie: cookie,
        Accept: 'application/json',
      },
    });

    if (!itemResp.ok) {
      return null;
    }

    const item = await itemResp.json();
    if (!item.abilities?.retrieve) {
      return null;
    }

    // Get the current user info from the /users/me/ endpoint
    // (not /users/ which is rate-limited)
    const userUrl = `${DRIVE_API_URL}/api/v1.0/users/me/`;
    const userResp = await fetch(userUrl, {
      headers: {
        Cookie: cookie,
        Accept: 'application/json',
      },
    });

    if (!userResp.ok) {
      return null;
    }

    const user = await userResp.json();

    if (!user?.sub) {
      return null;
    }

    return {
      userId: user.sub,
      userName: user.full_name || user.email || 'Anonymous',
      canEdit: !!item.abilities?.update,
    };
  } catch (err) {
    console.error('[relay] Auth failed:', err);
    return null;
  }
}

// --- Room management ---

interface Room {
  peers: Map<WebSocket, PeerMeta>;
  /**
   * Last time we broadcast a rate-limited room-wide signal
   * (`peer:state-request`, `peer:needs-save` legacy path). Prevents a
   * rapid reconnect loop from flooding peers.
   */
  lastNeedsSaveBroadcastMs: number;
  /**
   * Last timestamp (ms) we stamped onto a binary frame in this room.
   * We advance it with `max(Date.now(), lastStampedMs + 1)` so the stamp
   * is STRICTLY monotonic even when several frames arrive in the same
   * millisecond or the system clock jumps backwards. The stamp doubles
   * as a total-order seq for clients that need to arbitrate concurrent
   * submissions (e.g. lock requests). Wall-time drift caused by collision
   * bump-ups is bounded by the instantaneous burst size and self-heals as
   * soon as a clock tick passes without a new frame.
   */
  lastStampedMs: number;
}

interface PeerMeta {
  userId: string;
  userName: string;
  canEdit: boolean;
  joinedAt: number;
  pongReceived: boolean;
  pingTimer: ReturnType<typeof setInterval> | null;
  /**
   * True once this peer has broadcast `peer:crashed`. Persisted on
   * the relay so a late joiner sees the crashed flag in its
   * `room:state` snapshot and can exclude the peer from leader
   * election without having to witness the original broadcast.
   */
  crashed: boolean;
}

const rooms = new Map<string, Room>();

function getOrCreateRoom(roomId: string): Room {
  let room = rooms.get(roomId);
  if (!room) {
    room = {
      peers: new Map(),
      lastNeedsSaveBroadcastMs: 0,
      lastStampedMs: 0,
    };
    rooms.set(roomId, room);
  }
  return room;
}

function removeFromRoom(roomId: string, ws: WebSocket): void {
  const room = rooms.get(roomId);
  if (!room) return;

  const meta = room.peers.get(ws);
  if (meta?.pingTimer) clearInterval(meta.pingTimer);

  room.peers.delete(ws);

  if (room.peers.size === 0) {
    rooms.delete(roomId);
  } else {
    broadcastSystem(room, ws, {
      type: 'peer:leave',
      userId: meta?.userId,
    });
  }
}

// --- Message sending ---

function sendRaw(ws: WebSocket, data: RawData | string): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(data, {}, err => {
      if (err) ws.close();
    });
  }
}

function sendJSON(ws: WebSocket, msg: object): void {
  sendRaw(ws, JSON.stringify(msg));
}

function broadcastRaw(room: Room, sender: WebSocket, data: RawData): void {
  for (const [peer] of room.peers) {
    if (peer !== sender) {
      sendRaw(peer, data);
    }
  }
}

function broadcastSystem(room: Room, sender: WebSocket, msg: object): void {
  const data = JSON.stringify(msg);
  for (const [peer] of room.peers) {
    if (peer !== sender) {
      sendRaw(peer, data);
    }
  }
}

// --- Connection handling ---

function handleConnection(
  ws: WebSocket,
  roomId: string,
  auth: AuthResult,
  joinedAt: number
): void {
  ws.binaryType = 'arraybuffer';

  const room = getOrCreateRoom(roomId);

  const meta: PeerMeta = {
    userId: auth.userId,
    userName: auth.userName,
    canEdit: auth.canEdit,
    joinedAt,
    pongReceived: true,
    pingTimer: null,
    crashed: false,
  };

  room.peers.set(ws, meta);

  // Ping/pong keepalive
  meta.pingTimer = setInterval(() => {
    if (!meta.pongReceived) {
      ws.close();
      return;
    }
    meta.pongReceived = false;
    ws.ping();
  }, PING_INTERVAL_MS);

  ws.on('pong', () => {
    meta.pongReceived = true;
  });

  ws.on('error', () => {
    ws.close();
  });

  // IMPORTANT: the ws library (v8+) delivers BOTH text and binary frames as
  // Buffer. The `isBinary` second argument is the ONLY reliable way to tell
  // them apart — `typeof data === 'string'` is never true here. Miss this
  // and every client text frame (including `save:committed`) falls into the
  // binary branch, gets broadcast to every peer, and pollutes history.
  ws.on('message', (data: RawData, isBinary: boolean) => {
    // Text = system message. Always consume the text path here — a text
    // frame must never fall through to the encrypted-binary branch.
    if (!isBinary) {
      const text = Buffer.isBuffer(data)
        ? data.toString('utf-8')
        : typeof data === 'string'
          ? (data as string)
          : Buffer.from(data as ArrayBuffer).toString('utf-8');
      try {
        const msg = JSON.parse(text);
        handleSystemMessage(room, ws, meta, msg);
      } catch {
        // Malformed text frame — drop silently.
      }
      return;
    }

    // Read-only users can't send patches
    if (!meta.canEdit) {
      return;
    }

    // Binary = encrypted OT patch — relay to all OTHER peers.
    // ws delivers binary frames as Buffer, ArrayBuffer, or Buffer[]
    // depending on version/fragmentation. Normalize to a Buffer so the
    // history replay and broadcast paths have one concrete type.
    let binary: Buffer;
    if (Buffer.isBuffer(data)) {
      binary = data;
    } else if (Array.isArray(data)) {
      binary = Buffer.concat(data);
    } else if (data instanceof ArrayBuffer) {
      binary = Buffer.from(data);
    } else {
      console.warn('[relay] dropped unknown binary frame type');
      return;
    }
    // Reject frames too small to be a valid vault envelope (nonce+tag+...).
    if (binary.byteLength < 32) {
      console.warn('[relay] dropped tiny binary frame size:', binary.byteLength);
      return;
    }
    // Server-authoritative timestamp: prepend 8 bytes (big-endian u64
    // ms) to every frame. Serves as a total-order seq for replicated-
    // state arbitration (Word lock requests). Strictly monotonic — two
    // frames in the same ms are bumped to +1ms — so competing requests
    // always have a unique winner. We no longer persist history on the
    // relay: peer-to-peer state transfer (baseBin + chain shipped
    // directly between editor tabs) handles joiner catch-up.
    const now = Date.now();
    const timestampMs =
      now > room.lastStampedMs ? now : room.lastStampedMs + 1;
    room.lastStampedMs = timestampMs;
    const stamped = Buffer.allocUnsafe(8 + binary.byteLength);
    stamped.writeBigUInt64BE(BigInt(timestampMs), 0);
    binary.copy(stamped, 8);
    broadcastRaw(room, ws, stamped);

    // Tell the sender the relay has assigned this timestamp and
    // enqueued the broadcast to every peer. TCP FIFO on each peer's
    // socket guarantees ordering up to `timestampMs` — used by the
    // lock arbitrator to apply its own request to local state only
    // once it's certain no earlier competing request exists.
    sendJSON(ws, { type: 'frame:settled', timestampMs });
  });

  ws.on('close', () => {
    removeFromRoom(roomId, ws);
  });

  // Notify existing peers about the new joiner (always crashed:false
  // for a fresh connection — reconnecting a crashed tab counts as a
  // new PeerMeta).
  broadcastSystem(room, ws, {
    type: 'peer:join',
    userId: meta.userId,
    userName: meta.userName,
    canEdit: meta.canEdit,
    joinedAt: meta.joinedAt,
    crashed: meta.crashed,
  });

  // Send room state to the new joiner, including per-peer crashed
  // flags so a late arrival learns about already-crashed peers
  // without needing to witness the original broadcast.
  const peerList = Array.from(room.peers.entries())
    .filter(([peer]) => peer !== ws)
    .map(([, m]) => ({
      userId: m.userId,
      userName: m.userName,
      canEdit: m.canEdit,
      joinedAt: m.joinedAt,
      crashed: m.crashed,
    }));

  // No server-side history replay anymore — the joiner asks a peer
  // for live state via `peer:state-request` and receives an encrypted
  // `oo:state-response` carrying baseBin + chain. We still emit a
  // `history:end` marker so the client's preload state machine (which
  // waits for it before constructing OO) advances.
  sendJSON(ws, {
    type: 'room:state',
    peers: peerList,
  });
  sendJSON(ws, { type: 'history:end' });
}

// Only non-encrypted system messages are parsed by the relay.
// cursor:update and lock:acquire/release are now encrypted (sent as binary)
// and relayed opaquely without parsing.
const RELAYED_TYPES = new Set<string>([
  'save:lock',
  'save:unlock',
]);

function handleSystemMessage(
  room: Room,
  ws: WebSocket,
  meta: PeerMeta,
  msg: { type: string; [key: string]: unknown }
): void {
  if (msg.type === 'save:committed') {
    // Rebroadcast purely as a "please clear your unsaved-changes
    // marker" signal. The relay is pure transport — no history,
    // no anchoring; live state alignment is peer-to-peer.
    broadcastSystem(room, ws, {
      type: 'save:committed',
      userId: meta.userId,
    });
    return;
  }
  if (msg.type === 'peer:crashed') {
    // Persist on the connection so late joiners learn about it via
    // their initial `room:state` snapshot — the broadcast below only
    // reaches peers already in the room, so without this a peer who
    // joins after the crash would happily elect the dead tab leader.
    meta.crashed = true;
    broadcastSystem(room, ws, {
      type: 'peer:crashed',
      userId: meta.userId,
    });
    return;
  }
  if (msg.type === 'peer:state-request') {
    // A joining peer asking for live state. Broadcast to every other
    // peer; only the leader on the receive side will answer (with an
    // encrypted `oo:state-response` binary frame carrying baseBin +
    // chain). Rate-limited to absorb the case of two joiners landing
    // within the same moment — the second one still gets the response
    // because state-response is targeted at userId.
    const now = Date.now();
    if (now - room.lastNeedsSaveBroadcastMs < 2000) {
      return;
    }
    room.lastNeedsSaveBroadcastMs = now;
    broadcastSystem(room, ws, {
      type: 'peer:state-request',
      userId: meta.userId,
    });
    return;
  }
  if (RELAYED_TYPES.has(msg.type)) {
    // Inject the authenticated userId (server-authoritative, not client-supplied)
    broadcastSystem(room, ws, { ...msg, userId: meta.userId });
  }
  // Unknown types are silently dropped
}

// --- Server setup ---

const httpServer = createServer((_req, res) => {
  if (_req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        status: 'ok',
        rooms: rooms.size,
        connections: Array.from(rooms.values()).reduce(
          (n, r) => n + r.peers.size,
          0
        ),
      })
    );
    return;
  }
  res.writeHead(404);
  res.end();
});

const wss = new WebSocketServer({
  server: httpServer,
  maxPayload: MAX_PAYLOAD_BYTES,
});

wss.on('connection', async (ws, req) => {
  const url = new URL(req.url || '/', 'ws://localhost');
  const roomId = url.searchParams.get('room');
  if (!roomId) {
    ws.close(1008, 'room parameter required');
    return;
  }

  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      roomId
    )
  ) {
    ws.close(1008, 'invalid room id');
    return;
  }

  // Authenticate: verify session cookie + item access
  const auth = await authenticateConnection(req, roomId);

  if (!auth) {
    ws.close(1008, 'unauthorized');
    return;
  }

  // Compute joinedAt once so the authenticated frame and the PeerMeta
  // share exactly the same value — clients use it as a tiebreaker for
  // leader election when multiple peers share a userId (same human in
  // two tabs).
  const joinedAt = Date.now();

  // Confirm authentication to the client
  ws.send(
    JSON.stringify({
      type: 'system:authenticated',
      userId: auth.userId,
      userName: auth.userName,
      joinedAt,
    })
  );

  console.log(
    `[relay] ${auth.userName} (${auth.userId}) joined room ${roomId} (canEdit: ${auth.canEdit}) joinedAt=${joinedAt}`
  );

  handleConnection(ws, roomId, auth, joinedAt);
});

httpServer.listen(PORT, () => {
  console.log(`[relay] Collaboration relay server listening on port ${PORT}`);
});
