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
import { Mutex } from 'async-mutex';

const PORT = parseInt(process.env.RELAY_PORT || '4100', 10);
const DRIVE_API_URL = process.env.DRIVE_API_URL || 'http://app-dev:8000';
const PING_INTERVAL_MS = 30_000;
/**
 * Grace period between a `save:committed` message and the actual purge of
 * events whose timestamp is <= the committed epoch. The delay exists so a
 * joiner who just fetched an older snapshot (epoch N-2) still finds the
 * events that bring them up to epoch N-1 in the relay history.
 */
const HISTORY_PURGE_DELAY_MS = 10_000;
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

interface HistoryEntry {
  timestampMs: number;
  data: RawData;
}

interface Room {
  peers: Map<WebSocket, PeerMeta>;
  history: HistoryEntry[];
  /** Serializes delayed history purges against each other. */
  purgeMutex: Mutex;
  /**
   * Highest epoch (client UTC ms) we have ever purged history below. A
   * joiner reconnecting with `?since=X` where `X < historyFloorMs` is
   * asking for events we no longer remember, so we reject them and they
   * must refetch from S3.
   */
  historyFloorMs: number;
}

interface PeerMeta {
  userId: string;
  userName: string;
  canEdit: boolean;
  joinedAt: number;
  pongReceived: boolean;
  pingTimer: ReturnType<typeof setInterval> | null;
}

const rooms = new Map<string, Room>();

function getOrCreateRoom(roomId: string): Room {
  let room = rooms.get(roomId);
  if (!room) {
    room = {
      peers: new Map(),
      history: [],
      purgeMutex: new Mutex(),
      historyFloorMs: 0,
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
  sinceTimestampMs: number,
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
    // Server-authoritative timestamp: prepend 8 bytes (big-endian u64 ms)
    // to every frame so peers can advance their `sinceTimestampMs` cursor
    // monotonically across reconnects. The prefixed buffer is both
    // broadcast and stored in history so replay and live paths are
    // identical on the wire.
    const timestampMs = Date.now();
    const stamped = Buffer.allocUnsafe(8 + binary.byteLength);
    stamped.writeBigUInt64BE(BigInt(timestampMs), 0);
    binary.copy(stamped, 8);
    broadcastRaw(room, ws, stamped);
    room.history.push({ timestampMs, data: stamped });
  });

  ws.on('close', () => {
    removeFromRoom(roomId, ws);
  });

  // Notify existing peers about the new joiner
  broadcastSystem(room, ws, {
    type: 'peer:join',
    userId: meta.userId,
    userName: meta.userName,
    canEdit: meta.canEdit,
    joinedAt: meta.joinedAt,
  });

  // Send room state to the new joiner
  const peerList = Array.from(room.peers.entries())
    .filter(([peer]) => peer !== ws)
    .map(([, m]) => ({
      userId: m.userId,
      userName: m.userName,
      canEdit: m.canEdit,
      joinedAt: m.joinedAt,
    }));

  // Filter history to events strictly newer than the snapshot epoch the
  // joiner already has baked in (from S3 metadata). sinceTimestampMs = 0 means
  // "no snapshot" — send everything we have.
  const replay = room.history.filter(
    e => e.timestampMs > sinceTimestampMs
  );
  console.log(
    `[relay] replay for ${auth.userId}: since=${sinceTimestampMs} ` +
      `historySize=${room.history.length} replay=${replay.length} ` +
      `floor=${room.historyFloorMs}`,
  );

  sendJSON(ws, {
    type: 'room:state',
    peers: peerList,
    historyLength: replay.length,
    sinceTimestampMs,
  });

  for (const entry of replay) {
    sendRaw(ws, entry.data);
  }

  // End-of-history marker: the client holds off constructing the OO editor
  // until this fires so it can feed the replay to OO via `getInitialChanges`
  // instead of racing the post-load `sendMessageToOO` path.
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
    const epochMs = Number(msg.epochMs);
    if (!Number.isFinite(epochMs) || epochMs <= 0) return;
    scheduleHistoryPurge(room, epochMs);
    // Rebroadcast to other peers so they can clear their local
    // "unsaved changes" marker. The beforeunload guard on non-leader
    // peers otherwise shows the confirm modal even though the leader
    // already persisted the shared state.
    broadcastSystem(room, ws, {
      type: 'save:committed',
      epochMs,
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

/**
 * Delayed purge of history events older than the committed snapshot epoch.
 * The grace window lets joiners mid-fetch still pick up events that bridge
 * their older snapshot to the newly-committed one.
 */
function scheduleHistoryPurge(room: Room, epochMs: number): void {
  setTimeout(() => {
    room.purgeMutex.runExclusive(() => {
      const before = room.history.length;
      room.history = room.history.filter(e => e.timestampMs > epochMs);
      const removed = before - room.history.length;
      // Advance the floor only after the purge actually executes (not at
      // schedule time) so the 10s grace window still lets a joiner with
      // an older snapshot fetch the bridging events.
      if (epochMs > room.historyFloorMs) {
        room.historyFloorMs = epochMs;
      }
      if (removed > 0) {
        console.log(
          `[relay] purged ${removed} history entries <= epoch ${epochMs}, floor=${room.historyFloorMs}`
        );
      }
    });
  }, HISTORY_PURGE_DELAY_MS);
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
  const sinceRaw = url.searchParams.get('since');
  const sinceTimestampMs = sinceRaw ? Number(sinceRaw) : 0;

  if (!roomId) {
    ws.close(1008, 'room parameter required');
    return;
  }

  if (!Number.isFinite(sinceTimestampMs) || sinceTimestampMs < 0) {
    ws.close(1008, 'invalid since parameter');
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

  // Stale-history guard: if the joiner's cursor is older than our purge
  // floor, we can no longer bring them up to date from memory. Tell them
  // to refetch the S3 snapshot and retry. Only applies when the client
  // actually has a snapshot (since > 0); a fresh cold-open with since=0
  // is always welcome to replay whatever history remains.
  const existingRoom = rooms.get(roomId);
  if (
    sinceTimestampMs > 0 &&
    existingRoom &&
    sinceTimestampMs < existingRoom.historyFloorMs
  ) {
    console.log(
      `[relay] stale history for ${auth.userId}: since=${sinceTimestampMs} < floor=${existingRoom.historyFloorMs}`
    );
    ws.close(4001, 'stale history — refetch snapshot');
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

  handleConnection(ws, roomId, auth, sinceTimestampMs, joinedAt);
});

httpServer.listen(PORT, () => {
  console.log(`[relay] Collaboration relay server listening on port ${PORT}`);
});
