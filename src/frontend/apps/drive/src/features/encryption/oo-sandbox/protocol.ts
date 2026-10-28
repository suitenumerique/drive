/**
 * Messages between Drive and the OnlyOffice sandbox: the page, served from its
 * own origin, that runs OnlyOffice and x2t on one decrypted document.
 *
 * Drive keeps the session, the vault, the API and the encrypted relay. The
 * sandbox gets the plaintext of the document it edits and nothing else; it
 * asks Drive for everything that needs a key or the network through `rpc`
 * messages limited to `SANDBOX_RPC_METHODS`. Drive treats every message from
 * the sandbox as untrusted input: `parseSandboxMessage` checks its shape and
 * size before anything acts on it.
 *
 * Both sides talk over a MessageChannel. Drive transfers one port to the
 * sandbox's origin only (`postMessage(..., sandboxOrigin, [port])`), so no
 * other window or frame can read or inject messages.
 */

export const ONLYOFFICE_SANDBOX_PROTOCOL = 1;

/** The first message, on `window`, that carries the port. */
export const SANDBOX_CONNECT = "drive-onlyoffice-sandbox:connect";

/** Largest document or export the sandbox may hand back to Drive. */
export const MAX_SANDBOX_FILE_BYTES = 200 * 1024 * 1024;

export type PeerStateDump = {
  baseBin: string;
  chain: Array<Record<string, unknown>>;
};

export type SandboxInit = {
  protocol: number;
  itemId: string;
  title: string;
  /** Effective mimetype of the file, from which the sandbox picks the editor. */
  mimetype: string;
  /** The decrypted file, transferred. */
  document: ArrayBuffer;
  user: { id: string; name: string; language: string };
  canEdit: boolean;
  /** Open locally without the relay: nothing is sent to the room. */
  viewOnly: boolean;
  /** Live state another editor shipped before the previous editor was torn down. */
  peerState: PeerStateDump | null;
  development: boolean;
};

/** Relay callbacks Drive forwards to the sandbox, by name. */
export const RELAY_EVENTS = [
  "onSaveChanges",
  "onHistoryEnd",
  "onPeerJoin",
  "onPeerLeave",
  "onRoomState",
  "onLockUpdate",
  "onCursorUpdate",
  "onMessageBroadcast",
  "onMetaBroadcast",
  "onSaveLock",
  "onConnectionChange",
  "onReconnectFailed",
  "onRemoteSaveCommitted",
  "onPeerNeedsSave",
  "onPeerCrashed",
  "onArbitratedLockRequest",
  "onArbitratedLockRelease",
  "onPeerStateRequest",
  "onPeerStateResponse",
  "onCheckpointReload",
] as const;
export type RelayEventName = (typeof RELAY_EVENTS)[number];

export type SandboxCommand = "forceSave" | "recover";

export type HostToSandbox =
  | { type: "init"; init: SandboxInit }
  | {
      type: "relay:event";
      name: RelayEventName;
      args: unknown[];
      /** The relay's `joinedAt`, read by leader election. */
      joinedAt: number | null;
    }
  | { type: "rpc:result"; id: number; ok: true; value?: unknown }
  | { type: "rpc:result"; id: number; ok: false; error: string }
  | { type: "command"; id: number; name: SandboxCommand };

/**
 * What the sandbox may ask Drive to do. The relay methods only reach the
 * room of the document being edited, as any editor of it can.
 */
export const SANDBOX_RPC_METHODS = [
  "relay.connect",
  "relay.sendSaveChanges",
  "relay.sendLock",
  "relay.sendCursor",
  "relay.sendMessage",
  "relay.sendMeta",
  "relay.sendCrashed",
  "relay.sendStateRequest",
  "relay.sendStateResponse",
  "relay.sendCheckpointReload",
  "relay.sendEncryptedWithSettlement",
  "relay.queuePendingMedia",
  "upload",
] as const;
export type SandboxRpcMethod = (typeof SANDBOX_RPC_METHODS)[number];

/** Phases the sandbox reports; Drive owns the others (decrypting, errors). */
export const ENGINE_PHASES = [
  "loading",
  "converting",
  "syncing-history",
  "ready",
  "peer-resyncing",
  "oo-crashed",
] as const;
export type EnginePhase = (typeof ENGINE_PHASES)[number];

/** `detail` is only logged by Drive. */
export type SaveResult = { kind: "fatal" | "transient"; detail: string } | null;

export type SandboxToHost =
  | { type: "ready" }
  | { type: "phase"; phase: EnginePhase }
  /** Drive shows its own text for `code`: `message` is only logged. */
  | { type: "failure"; code: string | null; message: string }
  | {
      type: "reinit";
      phase: "stale-resyncing" | "peer-resyncing";
      peerState: PeerStateDump | null;
    }
  | { type: "save-result"; result: SaveResult }
  | { type: "status"; unsavedAsLeader: boolean }
  | { type: "recovery"; waiting: boolean }
  | { type: "rpc"; id: number; method: SandboxRpcMethod; args: unknown[] }
  | {
      type: "export";
      mode: "download" | "print";
      extension: string;
      title: string;
      bytes: ArrayBuffer;
    }
  | { type: "command:result"; id: number; ok: boolean; error?: string };

/** Formats the sandbox may export, with the type Drive gives the file. */
export const EXPORT_MIME_BY_EXTENSION: Record<string, string> = {
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  doc: "application/msword",
  odt: "application/vnd.oasis.opendocument.text",
  rtf: "application/rtf",
  txt: "text/plain",
  html: "text/html",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  xls: "application/vnd.ms-excel",
  ods: "application/vnd.oasis.opendocument.spreadsheet",
  csv: "text/csv",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ppt: "application/vnd.ms-powerpoint",
  odp: "application/vnd.oasis.opendocument.presentation",
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isString = (value: unknown, max: number): value is string =>
  typeof value === "string" && value.length <= max;

const isId = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;

const isPeerStateDump = (value: unknown): value is PeerStateDump =>
  isRecord(value) &&
  typeof value.baseBin === "string" &&
  Array.isArray(value.chain) &&
  value.chain.every(isRecord);

/**
 * The arguments each RPC method accepts, checked before Drive calls the
 * relay or uploads. Payloads (OnlyOffice changes, locks, cursors) stay
 * opaque: the relay encrypts them as they are for the other editors.
 */
const RPC_ARGUMENTS: Record<SandboxRpcMethod, (args: unknown[]) => boolean> = {
  "relay.connect": (args) => args.length === 0,
  "relay.sendSaveChanges": (args) => args.length === 1 && isRecord(args[0]),
  "relay.sendLock": (args) =>
    args.length === 2 && (args[0] === "acquire" || args[0] === "release"),
  "relay.sendCursor": (args) => args.length === 1,
  "relay.sendMessage": (args) => args.length === 1 && Array.isArray(args[0]),
  "relay.sendMeta": (args) => args.length === 1 && Array.isArray(args[0]),
  "relay.sendCrashed": (args) => args.length === 0,
  "relay.sendStateRequest": (args) => args.length === 0,
  "relay.sendStateResponse": (args) =>
    args.length === 3 &&
    isString(args[0], 1024) &&
    typeof args[1] === "string" &&
    Array.isArray(args[2]) &&
    args[2].every(isRecord),
  "relay.sendCheckpointReload": (args) =>
    args.length === 1 && typeof args[0] === "string",
  "relay.sendEncryptedWithSettlement": (args) =>
    args.length === 1 && isRecord(args[0]),
  "relay.queuePendingMedia": (args) =>
    args.length === 2 &&
    isString(args[0], 1024) &&
    isString(args[1], MAX_SANDBOX_FILE_BYTES * 2) &&
    args[1].startsWith("data:image/"),
  upload: (args) =>
    args.length === 2 &&
    args[0] instanceof ArrayBuffer &&
    args[0].byteLength <= MAX_SANDBOX_FILE_BYTES &&
    isString(args[1], 16),
};

/** A message from the sandbox, or null when it is not one Drive accepts. */
export function parseSandboxMessage(data: unknown): SandboxToHost | null {
  if (!isRecord(data) || typeof data.type !== "string") return null;
  switch (data.type) {
    case "ready":
      return { type: "ready" };
    case "phase":
      return (ENGINE_PHASES as readonly unknown[]).includes(data.phase)
        ? { type: "phase", phase: data.phase as EnginePhase }
        : null;
    case "failure":
      if (data.code !== null && !isString(data.code, 64)) return null;
      if (!isString(data.message, 2000)) return null;
      return { type: "failure", code: data.code, message: data.message };
    case "reinit":
      if (data.phase !== "stale-resyncing" && data.phase !== "peer-resyncing")
        return null;
      if (data.peerState !== null && !isPeerStateDump(data.peerState))
        return null;
      return { type: "reinit", phase: data.phase, peerState: data.peerState };
    case "save-result": {
      const result = data.result;
      if (result === null) return { type: "save-result", result: null };
      if (
        !isRecord(result) ||
        (result.kind !== "fatal" && result.kind !== "transient") ||
        !isString(result.detail, 2000)
      )
        return null;
      return {
        type: "save-result",
        result: { kind: result.kind, detail: result.detail },
      };
    }
    case "status":
      return typeof data.unsavedAsLeader === "boolean"
        ? { type: "status", unsavedAsLeader: data.unsavedAsLeader }
        : null;
    case "recovery":
      return typeof data.waiting === "boolean"
        ? { type: "recovery", waiting: data.waiting }
        : null;
    case "rpc": {
      if (!isId(data.id) || !Array.isArray(data.args)) return null;
      const method = data.method as SandboxRpcMethod;
      if (!(SANDBOX_RPC_METHODS as readonly unknown[]).includes(method))
        return null;
      if (!RPC_ARGUMENTS[method](data.args)) return null;
      return { type: "rpc", id: data.id, method, args: data.args };
    }
    case "export": {
      if (data.mode !== "download" && data.mode !== "print") return null;
      if (
        !isString(data.extension, 8) ||
        !(data.extension in EXPORT_MIME_BY_EXTENSION)
      )
        return null;
      if (!isString(data.title, 1024)) return null;
      if (
        !(data.bytes instanceof ArrayBuffer) ||
        data.bytes.byteLength > MAX_SANDBOX_FILE_BYTES
      )
        return null;
      // Printing opens the file in Drive's page: only a PDF is printed.
      if (data.mode === "print" && !isPdf(data.bytes)) return null;
      return {
        type: "export",
        mode: data.mode,
        extension: data.extension,
        title: data.title,
        bytes: data.bytes,
      };
    }
    case "command:result":
      if (!isId(data.id) || typeof data.ok !== "boolean") return null;
      if (data.error !== undefined && !isString(data.error, 2000)) return null;
      return {
        type: "command:result",
        id: data.id,
        ok: data.ok,
        error: data.error as string | undefined,
      };
    default:
      return null;
  }
}

const isPdf = (bytes: ArrayBuffer): boolean => {
  const head = new Uint8Array(bytes, 0, Math.min(5, bytes.byteLength));
  return String.fromCharCode(...head) === "%PDF-";
};

/**
 * The name under which Drive saves an export: the title the editor
 * proposes, reduced to a plain file name, always with the exported
 * extension.
 */
export function exportFileName(title: string, extension: string): string {
  const base = title
    .split(/[\\/]/)
    .pop()!
    .replace(/[\u0000-\u001f\u007f<>:"|?*]/g, "")
    .replace(/^\.+/, "")
    .trim();
  const stem = base.replace(/\.[^.]*$/, "") || "document";
  return `${stem}.${extension}`;
}
