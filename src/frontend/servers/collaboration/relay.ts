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
const MAX_HISTORY = 500;
const PING_INTERVAL_MS = 30_000;

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
  history: RawData[];
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
    room = { peers: new Map(), history: [] };
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

function sendRaw(ws: WebSocket, data: RawData): void {
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
  auth: AuthResult
): void {
  ws.binaryType = 'arraybuffer';

  const room = getOrCreateRoom(roomId);

  const meta: PeerMeta = {
    userId: auth.userId,
    userName: auth.userName,
    canEdit: auth.canEdit,
    joinedAt: Date.now(),
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

  ws.on('message', (data: RawData) => {
    // Read-only users can't send patches
    if (!meta.canEdit && data instanceof ArrayBuffer) {
      return;
    }

    // Text = system message
    if (typeof data === 'string') {
      try {
        const msg = JSON.parse(data);
        handleSystemMessage(room, ws, meta, msg);
        return;
      } catch {
        // Not JSON
      }
    }

    // Binary = encrypted OT patch — relay + store
    broadcastRaw(room, ws, data);
    room.history.push(data);
    if (room.history.length > MAX_HISTORY) {
      room.history.shift();
    }
  });

  ws.on('close', () => {
    removeFromRoom(roomId, ws);
  });

  // Notify existing peers about the new joiner
  broadcastSystem(room, ws, {
    type: 'peer:join',
    userId: meta.userId,
    userName: meta.userName,
  });

  // Send room state to the new joiner
  const peerList = Array.from(room.peers.entries())
    .filter(([peer]) => peer !== ws)
    .map(([, m]) => ({
      userId: m.userId,
      userName: m.userName,
    }));

  sendJSON(ws, {
    type: 'room:state',
    peers: peerList,
    historyLength: room.history.length,
  });

  // Send history to the new joiner
  for (const historyMsg of room.history) {
    sendRaw(ws, historyMsg);
  }
}

type SystemMessageType =
  | 'lock:acquire'
  | 'lock:release'
  | 'cursor:update'
  | 'save:lock'
  | 'save:unlock';

const RELAYED_TYPES = new Set<string>([
  'lock:acquire',
  'lock:release',
  'cursor:update',
  'save:lock',
  'save:unlock',
]);

function handleSystemMessage(
  room: Room,
  ws: WebSocket,
  meta: PeerMeta,
  msg: { type: string; [key: string]: unknown }
): void {
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

const wss = new WebSocketServer({ server: httpServer });

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

  // Confirm authentication to the client
  ws.send(
    JSON.stringify({
      type: 'system:authenticated',
      userId: auth.userId,
      userName: auth.userName,
    })
  );

  console.log(
    `[relay] ${auth.userName} (${auth.userId}) joined room ${roomId} (canEdit: ${auth.canEdit})`
  );

  handleConnection(ws, roomId, auth);
});

httpServer.listen(PORT, () => {
  console.log(`[relay] Collaboration relay server listening on port ${PORT}`);
});
