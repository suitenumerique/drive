/**
 * The encrypted-document editor session, run inside the OnlyOffice sandbox.
 *
 * It owns everything that touches OnlyOffice: x2t conversions, the mock
 * server standing in for the Document Server, the live-state transfer
 * between editors (base bin + chain of changes), leader election, the
 * replicated locks, periodic saves and crash detection. It never sees a key,
 * the session or the API: decrypting, encrypting, uploading and the
 * encrypted relay stay in Drive, reached through `bridge.call` (see
 * `protocol.ts`), and the relay's callbacks come back through
 * `onRelayEvent`.
 *
 * The OnlyOffice modules it drives hold module-level state: one sandbox page
 * runs one engine, and Drive loads a fresh page for every (re)start.
 */

import {
  convertFromInternal,
  convertFromInternalToPdf,
  convertToInternal,
} from "./x2tConverter";
import {
  EXTENSION_TO_X2T_TYPE,
  MIME_TO_DOC_TYPE,
  MIME_TO_EXTENSION,
  MIME_TO_OO_FILE_TYPE,
  MIME_TO_X2T_TYPE,
  type OOConfig,
} from "../oo-bridge/types";
import {
  addPeerLockShownToEditor,
  consumePeerLocksShownToEditor,
  createMockServerCallbacks,
  resetPeerLocksShownToEditor,
  sendToEditor,
  setEditorInstance,
  setVerboseSends,
} from "./mockServer";
import {
  addRemoteUser,
  buildConnectStateMessage,
  getRemoteOOInternalId,
  getUniqueOOId,
  initLocalUser,
  removeRemoteUser,
} from "./participants";
import { observeIncomingSaveChanges, resetPatchIndex } from "./changesPipeline";
import {
  dispatchRepublishNudge,
  inspectOutboundForRepublish,
  installUndoFlagHook,
  undoFiredRecently,
} from "./republishOnUndo";
import { LockArbitrator } from "./lockArbitrator";
import { withIncomingOTGate } from "./incomingOtGate";
import {
  acquireCellLock,
  releaseAllUserLocks,
  releaseCellLock,
  resetAllLocks,
} from "./locks";
import {
  forceSave,
  hasUnsavedChanges,
  initCheckpointing,
  markRemoteSaveCommitted,
  stopCheckpointing,
} from "./checkpointing";
import type {
  EnginePhase,
  PeerStateDump,
  RelayEventName,
  SandboxCommand,
  SandboxInit,
  SandboxRpcMethod,
  SandboxToHost,
} from "./protocol";

declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (placeholder: string, config: OOConfig) => OOEditor;
    };
  }
}

interface OOEditor {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
  connectMockServer: (callbacks: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
  sendMessageToOO: (msg: any) => void;
  asc_nativeGetFile: () => Uint8Array;
  destroyEditor: () => void;
  injectCSS?: (css: string) => void;
}

export type EngineBridge = {
  /** Notify Drive (everything but RPC). */
  emit: (message: Exclude<SandboxToHost, { type: "rpc" }>) => void;
  /** Ask Drive to act; rejects with Drive's error message. */
  call: (
    method: SandboxRpcMethod,
    args: unknown[],
    transfer?: Transferable[],
  ) => Promise<unknown>;
};

export type EngineHandle = {
  onRelayEvent: (
    name: RelayEventName,
    args: unknown[],
    joinedAt: number | null,
  ) => void;
  command: (name: SandboxCommand) => Promise<void>;
  destroy: () => void;
};

// Past this many characters of serialised chain, the leader snapshots the
// document and has every editor reload it as the new base bin: a joiner
// replays the whole chain, so this bounds join latency.
const CHECKPOINT_CHAIN_SIZE_BYTES = 50 * 1024 * 1024;

// The only OnlyOffice message types a peer may make us feed to OnlyOffice.
// Anything else (rpc, executeCommand, documentOpen, ...) would let a peer
// reach internal surfaces that are not meant to be peer-driven.
const INBOUND_ALLOWLIST: ReadonlySet<string> = new Set([
  "saveChanges",
  "cursor",
  "message",
  "meta",
  "getLock",
  "releaseLock",
  "connectState",
  "authChanges",
]);

function sendToEditorGuarded(msg: { type?: string } & Record<string, unknown>) {
  if (
    !msg ||
    typeof msg.type !== "string" ||
    !INBOUND_ALLOWLIST.has(msg.type)
  ) {
    console.warn("[onlyoffice] dropping inbound message of type", msg?.type);
    return;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
  sendToEditor(msg as any);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
const innerWindowOf = (): any =>
  (document.querySelector('iframe[name="frameEditor"]') as HTMLIFrameElement)
    ?.contentWindow ?? null;

const OO_API_SCRIPT = "/onlyoffice/v9/web-apps/apps/api/documents/api.js";

/** Load OnlyOffice's DocsAPI from this origin. */
export function loadOnlyOffice(): Promise<void> {
  if (window.DocsAPI) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = OO_API_SCRIPT;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load OnlyOffice API"));
    document.head.appendChild(script);
  });
}

// Any uncaught error from OnlyOffice's sdkjs leaves its model in an unknown
// state: treat it as a crash rather than listing known failures.
const isOOCrash = (src: string | undefined, msg: string): boolean => {
  if (src && /\/sdkjs\/|sdk-all/.test(src)) return true;
  return /sdk-all|\bAsc(?:Common|Format|Word)\b|CDocument\.|CCollaborative/.test(
    msg,
  );
};

const USER_PALETTE = [
  { r: 0xea, g: 0x44, b: 0x35 },
  { r: 0xfb, g: 0x8c, b: 0x00 },
  { r: 0xfd, g: 0xd8, b: 0x35 },
  { r: 0x7c, g: 0xb3, b: 0x42 },
  { r: 0x2e, g: 0x7d, b: 0x32 },
  { r: 0x00, g: 0xac, b: 0xc1 },
  { r: 0x16, g: 0x68, b: 0xdd },
  { r: 0x3f, g: 0x51, b: 0xb5 },
  { r: 0x7e, g: 0x57, b: 0xc2 },
  { r: 0xab, g: 0x47, b: 0xbc },
  { r: 0xec, g: 0x40, b: 0x7a },
  { r: 0x8d, g: 0x6e, b: 0x63 },
  { r: 0x55, g: 0x6c, b: 0x78 },
  { r: 0x00, g: 0x69, b: 0x7c },
  { r: 0xc6, g: 0x28, b: 0x28 },
  { r: 0x37, g: 0x47, b: 0x4f },
];

// Images are inlined as data URLs into the change records the relay
// carries, which caps payloads: refuse bigger ones with OnlyOffice's own
// "image too large" error.
const MAX_IMAGE_BYTES = 50 * 1024 * 1024;
const ASC_ERR_UPL_IMAGE_SIZE = -9;

const filesToDataURLs = async (files: FileList | File[]): Promise<string[]> => {
  const arr = Array.from(files);
  for (const f of arr) {
    if (f.size > MAX_IMAGE_BYTES) throw ASC_ERR_UPL_IMAGE_SIZE;
  }
  return Promise.all(
    arr.map(
      (file) =>
        new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as string);
          reader.onerror = () =>
            reject(reader.error ?? new Error("FileReader failed"));
          reader.readAsDataURL(file);
        }),
    ),
  );
};

const imageMime = (name: string): string => {
  const ext = (name.split(".").pop() || "png").toLowerCase();
  if (ext === "jpg" || ext === "jpeg") return "image/jpeg";
  if (ext === "gif") return "image/gif";
  if (ext === "svg") return "image/svg+xml";
  if (ext === "webp") return "image/webp";
  return "image/png";
};

const bytesToDataUrl = (bytes: Uint8Array, mime: string): string => {
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.byteLength; offset += chunkSize) {
    binary += String.fromCharCode.apply(
      null,
      Array.from(bytes.subarray(offset, offset + chunkSize)),
    );
  }
  return `data:${mime};base64,${btoa(binary)}`;
};

const toArrayBuffer = (bytes: Uint8Array): ArrayBuffer =>
  bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;

// Shape presets that do not survive x2t's ODP round-trip (custom path data
// its ODF writer and reader disagree on): hidden from the shape gallery.
const UNSUPPORTED_SHAPE_ICONS = new Set<string>([
  "svg-icon-frame",
  "svg-icon-snip2DiagRect",
  "svg-icon-mathNotEqual",
  "svg-icon-trapezoid",
  "svg-icon-parallelogram",
  "svg-icon-plus",
  "svg-icon-rightArrow",
  "svg-icon-leftArrow",
  "svg-icon-upArrow",
  "svg-icon-downArrow",
  "svg-icon-leftRightArrow",
  "svg-icon-upDownArrow",
  "svg-icon-quadArrow",
  "svg-icon-leftRightUpArrow",
  "svg-icon-bentArrow",
  "svg-icon-uturnArrow",
  "svg-icon-leftUpArrow",
  "svg-icon-bentUpArrow",
  "svg-icon-stripedRightArrow",
  "svg-icon-notchedRightArrow",
  "svg-icon-homePlate",
  "svg-icon-chevron",
  "svg-icon-rightArrowCallout",
  "svg-icon-downArrowCallout",
  "svg-icon-leftArrowCallout",
  "svg-icon-upArrowCallout",
  "svg-icon-leftRightArrowCallout",
  "svg-icon-quadArrowCallout",
]);

// Charts and SmartArt need the full Document Server: x2t cannot save them.
const UNSUPPORTED_BUTTONS = [
  {
    slotId: "slot-btn-insertchart",
    menuId: "id-toolbar-menu-insertchart",
    label: "Charts",
  },
  {
    slotId: "slot-btn-inschart",
    menuId: "id-toolbar-menu-inschart",
    label: "Charts",
  },
  {
    slotId: "slot-btn-inssmartart",
    menuId: "id-toolbar-menu-inssmartart",
    label: "SmartArt",
  },
];

type BinDecision = "peer" | "cold" | "no-response" | "no-relay";

export function startEngine(
  init: SandboxInit,
  bridge: EngineBridge,
): EngineHandle {
  let destroyed = false;
  let phase: EnginePhase = "loading";
  const setPhase = (next: EnginePhase) => {
    phase = next;
    bridge.emit({ type: "phase", phase: next });
  };

  const { canEdit, user } = init;
  const docType = MIME_TO_DOC_TYPE[init.mimetype] || "word";
  const ooFileType = MIME_TO_OO_FILE_TYPE[init.mimetype] || "docx";
  const x2tType = MIME_TO_X2T_TYPE[init.mimetype] || "doc";
  const x2tExtension = MIME_TO_EXTENSION[init.mimetype] || "docx";
  const filename = `document.${x2tExtension}`;

  // The relay lives in Drive; this mirrors the part of its interface the
  // session uses. Calls are no-ops until Drive confirms it connected.
  let relayActive = false;
  let relayJoinedAt: number | null = null;
  const relayCall = (method: SandboxRpcMethod, args: unknown[] = []) => {
    if (!relayActive) return;
    bridge.call(method, args).catch((e) => {
      console.warn(`[onlyoffice] ${method} failed`, e);
    });
  };
  const relay = {
    sendSaveChanges: (message: Record<string, unknown>) =>
      relayCall("relay.sendSaveChanges", [message]),
    sendLock: (type: "acquire" | "release", lockData: unknown) =>
      relayCall("relay.sendLock", [type, lockData]),
    sendCursor: (cursor: unknown) => relayCall("relay.sendCursor", [cursor]),
    sendMessage: (messages: unknown[]) =>
      relayCall("relay.sendMessage", [messages]),
    sendMeta: (messages: unknown[]) => relayCall("relay.sendMeta", [messages]),
    sendCrashed: () => relayCall("relay.sendCrashed"),
    sendStateRequest: () => relayCall("relay.sendStateRequest"),
    sendStateResponse: (
      toUserId: string,
      baseBin: string,
      chain: Array<Record<string, unknown>>,
    ) => relayCall("relay.sendStateResponse", [toUserId, baseBin, chain]),
    sendCheckpointReload: (baseBin: string) =>
      relayCall("relay.sendCheckpointReload", [baseBin]),
    queuePendingMedia: (name: string, dataUrl: string) =>
      relayCall("relay.queuePendingMedia", [name, dataUrl]),
    sendEncryptedWithSettlement: async (msg: object): Promise<number> => {
      if (!relayActive) throw new Error("relay not connected");
      return (await bridge.call("relay.sendEncryptedWithSettlement", [
        msg,
      ])) as number;
    },
  };

  let editor: OOEditor | null = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
  let innerWindow: any = null;
  let lockArbitrator: LockArbitrator | null = null;

  // Editors with edit rights in the room (not us), by user id, with the
  // earliest `joinedAt` seen for that user: the leader-election tiebreak.
  const editorPeers = new Map<string, number>();
  // Peers whose editor crashed: still connected (they wait for a save),
  // never elected.
  const crashedPeers = new Set<string>();

  // Live-state transfer: the native bin OnlyOffice loaded from, and every
  // saveChanges since, outgoing and incoming alike. A joiner loading the
  // same bin and replaying the same chain ends up with the same internal
  // object ids as us.
  let baseBin: string | null = null;
  let chain: Array<Record<string, unknown>> = [];
  let peerStateDump: PeerStateDump | null = init.peerState;
  let awaitingPeerState = false;
  let binDecisionResolve: ((r: BinDecision) => void) | null = null;

  // OnlyOffice drops external changes that land before its content is
  // ready: those are held in `replayBuffer` until then.
  let documentReady = false;
  let replayBuffer: Array<() => void> = [];
  let replayPreDelayActive = true;
  // Set once the editor is in an inconsistent state: nothing it emits may
  // reach the other editors, or one broken tab would crash the room.
  let outgoingSilenced = false;
  // A gate against the republish detector catching our own nudge.
  let autoRepublishGate = false;

  let recoveryWaiting = false;
  let recoveryResolve: (() => void) | null = null;
  const RECOVERY_SAVE_WAIT_MS = 10_000;

  const requestReinit = (
    next: "stale-resyncing" | "peer-resyncing",
    peerState: PeerStateDump | null,
  ) => {
    if (destroyed) return;
    bridge.emit({ type: "reinit", phase: next, peerState });
  };

  // Earliest `joinedAt` wins, the user id breaking ties: the longest-lived
  // editor is the most likely to hold the freshest state, and a newcomer
  // never steals the role from the editor it asks for state.
  const isSaveLeader = (): boolean => {
    if (!canEdit || outgoingSilenced) return false;
    const myJoinedAt = relayJoinedAt ?? 0;
    for (const [peerId, peerJoinedAt] of editorPeers) {
      if (crashedPeers.has(peerId)) continue;
      if (peerJoinedAt < myJoinedAt) return false;
      if (peerJoinedAt === myJoinedAt && peerId < user.id) return false;
    }
    return true;
  };

  // Drive needs it synchronously, to warn before the tab closes.
  let lastStatus: boolean | null = null;
  const publishStatus = () => {
    const unsavedAsLeader = isSaveLeader() && hasUnsavedChanges();
    if (unsavedAsLeader === lastStatus) return;
    lastStatus = unsavedAsLeader;
    bridge.emit({ type: "status", unsavedAsLeader });
  };
  const statusTimer = setInterval(publishStatus, 1000);

  const enterCrashState = () => {
    if (!outgoingSilenced) {
      console.warn("[onlyoffice] crash: outbound traffic silenced");
    }
    outgoingSilenced = true;
    // Surviving editors drop us from the election; we stay connected to
    // see the `save:committed` a recovery waits for.
    relay.sendCrashed();
    setPhase("oo-crashed");
  };

  const handleOOError = (event: ErrorEvent) => {
    if (destroyed) return;
    const src = event.filename ?? "";
    const msg = String(event.error?.stack ?? event.message ?? "");
    if (!isOOCrash(src, msg)) return;
    console.error("[onlyoffice] uncaught OnlyOffice crash", { src, msg });
    enterCrashState();
  };
  window.addEventListener("error", handleOOError);

  const requestRecoveryReload = async () => {
    if (recoveryWaiting) return;
    // Nobody else can save: reload from the stored document now.
    const hasOtherSaver = [...editorPeers.keys()].some(
      (id) => id !== user.id && !crashedPeers.has(id),
    );
    if (!hasOtherSaver) {
      requestReinit("stale-resyncing", null);
      return;
    }
    recoveryWaiting = true;
    bridge.emit({ type: "recovery", waiting: true });
    // Ask a surviving editor for its live state; without an answer in
    // time, reload from the stored document.
    relay.sendStateRequest();
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      recoveryResolve = null;
      recoveryWaiting = false;
      bridge.emit({ type: "recovery", waiting: false });
      requestReinit("stale-resyncing", null);
    };
    recoveryResolve = finish;
    setTimeout(finish, RECOVERY_SAVE_WAIT_MS);
  };

  // Changes are applied in arrival order (the relay keeps it), held back
  // until OnlyOffice settles after its content is ready.
  const handleIncomingSaveChanges = (applyFn: () => void) => {
    if (replayPreDelayActive) {
      replayBuffer.push(applyFn);
      return;
    }
    try {
      applyFn();
    } catch (e) {
      console.warn("[onlyoffice] apply error", e);
    }
  };

  const releaseReplay = () => {
    setTimeout(() => {
      replayPreDelayActive = false;
      setVerboseSends(true);
      const queue = replayBuffer;
      replayBuffer = [];
      for (const apply of queue) {
        try {
          apply();
        } catch (e) {
          console.warn("[onlyoffice] replay apply error", e);
        }
      }
      // Only now: the overlay hid the replay, the user sees the final
      // document at once.
      if (phase !== "ready" && phase !== "oo-crashed") setPhase("ready");
    }, 0);
  };

  // Cursors, locks and messages from before the document is ready are
  // dropped, not replayed: a lock announced on a paragraph OnlyOffice does
  // not know yet crashes it, and the others are refreshed by the next ones.
  const whenReady = (apply: () => void) => {
    if (documentReady) apply();
  };

  const applyGlobalBundleWorkarounds = () => {
    if (!editor?.injectCSS) return;
    // "Download as" targets the bundled x2t cannot write.
    const unsupported =
      docType === "word"
        ? ["epub", "fb2", "rtf", "jpg", "png"]
        : docType === "cell"
          ? ["xlsb"]
          : [];
    try {
      editor.injectCSS(
        unsupported
          .map(
            (ext) =>
              `.format-item:has(.svg-format-${ext}) { display: none !important; }`,
          )
          .join("\n"),
      );
    } catch (err) {
      console.warn(
        "[onlyoffice] injectCSS for unsupported formats failed",
        err,
      );
    }
  };

  // `permissions.edit: false` does not stop keystrokes: restrict the model
  // itself, which still applies the other editors' changes live.
  const applyReadOnlyRestriction = () => {
    if (canEdit) return;
    const win = innerWindowOf();
    if (!win) return;
    const ooEditor = docType === "cell" ? win.editorCell : win.editor;
    try {
      ooEditor?.asc_setRestriction?.(true);
    } catch (err) {
      console.warn("[onlyoffice] asc_setRestriction(true) failed", err);
    }
    try {
      editor?.injectCSS?.(
        [
          "#toolbar { display: none !important; }",
          "#chat-options { display: none !important; }",
        ].join("\n"),
      );
    } catch (err) {
      console.warn("[onlyoffice] injectCSS failed", err);
    }
    // Let OnlyOffice reclaim the space of the hidden bands.
    window.dispatchEvent(new Event("resize"));
    win.dispatchEvent(new Event("resize"));
  };

  // Right-click Paste in slides reads OnlyOffice's internal clipboard
  // (the full shape); Cmd+V goes through the browser's HTML clipboard and
  // only inserts a flat picture. Reroute the HTML path to `Paste()`, a tick
  // later so the paste helper frame gives the focus back first.
  const installSlidePasteWorkaround = () => {
    if (docType !== "slide") return;
    try {
      const ooEditor = innerWindowOf()?.editor;
      const proto = ooEditor && Object.getPrototypeOf(ooEditor);
      if (!proto || typeof proto.asc_PasteData !== "function") return;
      const original = proto.asc_PasteData;
      if (original.__driveSlidePasteWrapped) return;
      proto.asc_PasteData = function (
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
        this: any,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
        ...args: any[]
      ) {
        if (args[0] === 8 && typeof this.Paste === "function") {
          // eslint-disable-next-line @typescript-eslint/no-this-alias
          const self = this;
          setTimeout(() => {
            try {
              self.Paste();
            } catch (e) {
              console.warn("[onlyoffice] deferred slide Paste() threw", e);
            }
          }, 0);
          return false;
        }
        return original.apply(this, args);
      };
      proto.asc_PasteData.__driveSlidePasteWrapped = true;
    } catch (e) {
      console.warn("[onlyoffice] slide paste workaround failed", e);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
  const disableUnsupportedFeatures = (win: any) => {
    if (win.__driveUnsupportedDisabled) return;
    win.__driveUnsupportedDisabled = true;
    const doc = win.document;
    const apply = () => {
      for (const { slotId, menuId, label } of UNSUPPORTED_BUTTONS) {
        const slot = doc.getElementById(slotId) as HTMLElement | null;
        if (!slot) continue;
        slot.style.setProperty("opacity", "0.4", "important");
        slot.style.setProperty("pointer-events", "none", "important");
        slot.setAttribute(
          "title",
          `${label} is not available in encrypted documents`,
        );
        const btn = slot.querySelector("button") as HTMLElement | null;
        if (btn) {
          btn.setAttribute("tabindex", "-1");
          btn.setAttribute("aria-disabled", "true");
          btn.style.setProperty("cursor", "default", "important");
        }
        const menu = doc.getElementById(menuId);
        if (menu) menu.innerHTML = "";
      }
      doc
        .querySelectorAll(".menu-insert-shape .item, .recent-items .item")
        .forEach((item: Element) => {
          const use = item.querySelector("use");
          const href =
            use?.getAttribute("xlink:href") || use?.getAttribute("href") || "";
          if (UNSUPPORTED_SHAPE_ICONS.has(href.replace(/^#/, ""))) {
            (item as HTMLElement).style.setProperty(
              "display",
              "none",
              "important",
            );
          }
        });
    };
    apply();
    try {
      new win.MutationObserver(apply).observe(doc.body, {
        childList: true,
        subtree: true,
      });
    } catch (e) {
      console.warn("[onlyoffice] unsupported-features observer failed", e);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
  const patchInnerWindow = (win: any) => {
    // sdk-all errors fire on the editor frame's window, not ours.
    if (!win.__driveCrashHooked) {
      win.__driveCrashHooked = true;
      win.addEventListener("error", (evt: ErrorEvent) => handleOOError(evt));
      win.addEventListener(
        "unhandledrejection",
        (evt: PromiseRejectionEvent) => {
          handleOOError({
            filename: "",
            message: String(evt.reason?.stack ?? evt.reason ?? ""),
            error: evt.reason,
          } as ErrorEvent);
        },
      );
    }

    // The spell-check worker sometimes answers without the expected field
    // and `SpellCheck_CallBack` crashes on it; turning spell-check off does
    // not stop the worker. Replace it with an inert stub.
    if (!win.__driveSpellWorkerNeutralised && win.Worker) {
      win.__driveSpellWorkerNeutralised = true;
      const OrigWorker = win.Worker;
      const isSpellCheckUrl = (u: unknown) =>
        /\bspell(?:_ie)?\.js\b/.test(String(u)) ||
        /\/sdkjs\/.*spell/i.test(String(u));
      win.Worker = function PatchedWorker(
        url: string | URL,
        options?: WorkerOptions,
      ) {
        if (isSpellCheckUrl(url)) {
          const noop = () => undefined;
          return {
            postMessage: noop,
            terminate: noop,
            addEventListener: noop,
            removeEventListener: noop,
            dispatchEvent: () => false,
            onmessage: null,
            onerror: null,
            onmessageerror: null,
          } as unknown as Worker;
        }
        return new OrigWorker(url, options);
      } as unknown as typeof Worker;
      win.Worker.prototype = OrigWorker.prototype;
    }

    disableUnsupportedFeatures(win);

    // OnlyOffice creates its paste-sanitising frame with
    // sandbox="allow-same-origin", which breaks image paste: create it
    // first, under the id it looks for.
    const cb = win.AscCommon?.g_clipboardBase;
    if (cb && !win.document.getElementById(cb.CommonIframeId)) {
      const pasteIfr = win.document.createElement("iframe");
      pasteIfr.name = cb.CommonIframeId;
      pasteIfr.id = cb.CommonIframeId;
      Object.assign(pasteIfr.style, {
        position: "absolute",
        top: "-100px",
        left: "0px",
        width: "10000px",
        height: "100px",
        overflow: "hidden",
        zIndex: "-1000",
      });
      pasteIfr.setAttribute("sandbox", "allow-same-origin allow-scripts");
      win.document.body.appendChild(pasteIfr);
      cb.CommonIframe = pasteIfr;
    }

    // Pasted image URLs would be "uploaded" to a Document Server: register
    // them locally instead, and send their bytes with the next change.
    if (win.AscCommon && !win.AscCommon.__driveImgUrlsPatched) {
      let imgCounter = 0;
      win.AscCommon.sendImgUrls = function (
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
        api: any,
        images: unknown[],
        callback: (data: Array<{ url: string; path: string }>) => void,
      ) {
        const action = win.Asc?.c_oAscAsyncActionType?.BlockInteraction ?? 1;
        const load = win.Asc?.c_oAscAsyncAction?.LoadImage ?? 0;
        if (!api.isOpenedFrameEditor) api.sync_StartAction?.(action, load);
        const out: Array<{ url: string; path: string }> = [];
        const urls: Record<string, string> = {};
        for (const src of images) {
          if (typeof src !== "string") {
            out.push({ url: "error", path: "error" });
            continue;
          }
          const mimeMatch = /^data:image\/([a-z0-9+]+)/.exec(src);
          const ext = mimeMatch ? mimeMatch[1].replace("+xml", "") : "png";
          imgCounter += 1;
          const name = `image_${Date.now()}_${imgCounter}.${ext}`;
          const path = "media/" + name;
          urls[path] = src;
          out.push({ url: src, path });
          relay.queuePendingMedia(name, src);
        }
        win.AscCommon.g_oDocumentUrls.addUrls(urls);
        if (!api.isOpenedFrameEditor) api.sync_EndAction?.(action, load);
        callback(out);
      };
      win.AscCommon.__driveImgUrlsPatched = true;
    }

    const innerEditor = win.editor || win.editorCell;
    try {
      innerEditor?.asc_setSpellCheck?.(false);
    } catch (e) {
      console.warn("[onlyoffice] asc_setSpellCheck(false) failed", e);
    }

    // Edit-phase ids are prefixed per user by OnlyOffice; ours is empty
    // (attribution follows `config.user.id`), so two editors would both mint
    // `_1`. Pin a prefix unique per connection.
    try {
      win.AscCommon?.g_oIdCounter?.Set_UserId?.(
        `${user.id}_${relayJoinedAt ?? Date.now()}`,
      );
    } catch (e) {
      console.warn("[onlyoffice] Set_UserId override failed", e);
    }

    // Remember the target of a download or print: `printPdf` reads it.
    if (innerEditor) {
      let proto = Object.getPrototypeOf(innerEditor);
      while (
        proto &&
        !Object.prototype.hasOwnProperty.call(proto, "_downloadAsUsingServer")
      ) {
        proto = Object.getPrototypeOf(proto);
      }
      if (proto && !proto.__driveDownloadPatched) {
        const original = proto._downloadAsUsingServer;
        proto._downloadAsUsingServer = function (
          _actionType: unknown,
          _options: unknown,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
          oAdditionalData: any,
          _dataContainer: unknown,
          downloadType: unknown,
        ) {
          window.__driveDownloadCtx = {
            title: oAdditionalData?.title,
            outputformat: oAdditionalData?.outputformat,
            downloadType,
          };
          // eslint-disable-next-line prefer-rest-params, @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
          return original.apply(this, arguments as any);
        };
        proto.__driveDownloadPatched = true;
      }
    }
  };

  // Print and "Download as": OnlyOffice routes both through `printPdf`.
  // The sandbox converts; Drive saves or prints the result.
  const exportDocument = async (dataContainer: {
    data: Uint8Array | ArrayBuffer | null;
  }) => {
    const win = innerWindowOf();
    const innerEditor = win?.editor || win?.editorCell;
    if (!innerEditor?.asc_nativeGetFile) {
      throw new Error("inner editor not ready");
    }
    const rawBin = innerEditor.asc_nativeGetFile();
    if (!rawBin) throw new Error("empty document");
    const binBuffer: ArrayBuffer =
      typeof rawBin === "string"
        ? (new TextEncoder().encode(rawBin).buffer as ArrayBuffer)
        : rawBin instanceof ArrayBuffer
          ? rawBin
          : toArrayBuffer(rawBin);

    const ctx = window.__driveDownloadCtx ?? {};
    const title: string = ctx.title || `document.${x2tExtension}`;
    const ext = (title.split(".").pop() || x2tExtension).toLowerCase();
    const isPrint = ctx.downloadType === "asc_onPrintUrl";

    let outBytes: Uint8Array;
    if (ext === "pdf") {
      const rawLayout = dataContainer?.data;
      if (!rawLayout) throw new Error("missing PDF layout bin");
      const layoutBuffer =
        rawLayout instanceof ArrayBuffer ? rawLayout : toArrayBuffer(rawLayout);
      // The PDF writer reads images from media/: hand it every image the
      // document references, or a printed selection loses them.
      const media = new Map<string, Uint8Array>();
      const urls = win?.AscCommon?.g_oDocumentUrls?.getUrls?.() ?? {};
      await Promise.all(
        Object.entries(urls).map(async ([key, value]) => {
          if (typeof value !== "string") return;
          try {
            const resp = await fetch(value);
            if (!resp.ok) return;
            media.set(
              key.startsWith("media/") ? key.slice("media/".length) : key,
              new Uint8Array(await resp.arrayBuffer()),
            );
          } catch (e) {
            console.warn("[onlyoffice] failed to read image", key, e);
          }
        }),
      );
      outBytes = await convertFromInternalToPdf(binBuffer, layoutBuffer, media);
    } else {
      outBytes = await convertFromInternal(
        binBuffer,
        ext,
        EXTENSION_TO_X2T_TYPE[ext] || x2tType || "doc",
      );
    }
    const bytes = toArrayBuffer(outBytes);
    bridge.emit({
      type: "export",
      mode: isPrint ? "print" : "download",
      extension: ext,
      title,
      bytes,
    });
  };

  const installAppHooks = () => {
    const app = (window.APP ??= {});
    // Theme changes travel as ordinary changes: nothing to do here.
    app.changeTheme = () => undefined;
    app.remoteTheme = () => undefined;
    // Images go into the document as data URLs, never to a server.
    app.UploadImageFiles = (files, _documentId, _userId, _jwt, callback) => {
      filesToDataURLs(files)
        .then((urls) => callback(null, urls))
        .catch((err) => {
          if (err !== ASC_ERR_UPL_IMAGE_SIZE) {
            console.error("[onlyoffice] UploadImageFiles failed", err);
          }
          callback(ASC_ERR_UPL_IMAGE_SIZE, []);
        });
    };
    app.AddImage = (successCb, errorCb) => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      input.style.display = "none";
      input.addEventListener("change", () => {
        const file = input.files?.[0];
        document.body.removeChild(input);
        if (!file) {
          errorCb?.();
          return;
        }
        filesToDataURLs([file])
          .then(([url]) => successCb({ url, name: file.name }))
          .catch((err) => errorCb?.(err));
      });
      document.body.appendChild(input);
      input.click();
    };
    app.printPdf = (dataContainer, callback) => {
      exportDocument(dataContainer)
        .catch((err) => console.error("[onlyoffice] export failed", err))
        // null: OnlyOffice must not run its own download on top of ours.
        .finally(() => callback(null));
    };
    // One deterministic color per user, whichever OnlyOffice call site asks.
    app.getUserColor = (userId: string) => {
      if (!userId) return null;
      let hash = 0;
      for (let i = 0; i < userId.length; i++) {
        hash = (hash * 31 + userId.charCodeAt(i)) >>> 0;
      }
      const c = USER_PALETTE[hash % USER_PALETTE.length];
      return { r: c.r, g: c.g, b: c.b, a: 255 };
    };
  };

  const dropPeerLocks = (peerUserId: string, wipeTable: () => void) => {
    // Only release what OnlyOffice was told about: an unknown key crashes
    // its release handler.
    const keys = lockArbitrator
      ? lockArbitrator
          .snapshot()
          .filter((e) => e.userId === peerUserId)
          .map((e) => e.key)
      : [];
    const clearableKeys = consumePeerLocksShownToEditor(keys);
    const ooId = getRemoteOOInternalId(peerUserId) ?? peerUserId;
    wipeTable();
    if (documentReady && clearableKeys.length > 0) {
      sendToEditorGuarded({
        type: "releaseLock",
        locks: clearableKeys.map((key) => ({
          block: key,
          user: ooId,
          time: Date.now(),
        })),
      });
    }
  };

  let historyPhaseComplete = false;
  let resolveHistoryReady: () => void = () => {};
  const historyReady = new Promise<void>((resolve) => {
    resolveHistoryReady = resolve;
  });
  const historyInitialMedia: Record<string, string> = {};
  const endPreloadPhase = () => {
    if (historyPhaseComplete) return;
    historyPhaseComplete = true;
    resolveHistoryReady();
  };

  const otherLiveEditors = () =>
    [...editorPeers.keys()].filter(
      (id) => id !== user.id && !crashedPeers.has(id),
    );

  const relayCallbacks: Record<RelayEventName, (...args: never[]) => void> = {
    onSaveChanges: (
      _userId: string,
      message: Record<string, unknown>,
      media?: Record<string, string>,
    ) => {
      if (media) {
        if (!historyPhaseComplete) {
          Object.assign(historyInitialMedia, media);
        } else {
          try {
            const docUrls = innerWindow?.AscCommon?.g_oDocumentUrls;
            for (const [name, url] of Object.entries(media)) {
              docUrls?.addImageUrl(name, url);
            }
          } catch (e) {
            console.warn("[onlyoffice] failed to register inbound media", e);
          }
        }
      }
      chain.push(message);
      handleIncomingSaveChanges(() => {
        observeIncomingSaveChanges(message);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
        withIncomingOTGate(() => sendToEditorGuarded(message as any));
      });
      publishStatus();
    },
    onHistoryEnd: () => endPreloadPhase(),
    onPeerJoin: (
      userId: string,
      userName: string,
      peerCanEdit: boolean,
      joinedAt: number,
    ) => {
      if (peerCanEdit) {
        const existing = editorPeers.get(userId);
        if (existing === undefined || joinedAt < existing) {
          editorPeers.set(userId, joinedAt);
        }
      }
      addRemoteUser(userId, userName, userId);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
      sendToEditor(buildConnectStateMessage() as any);
      publishStatus();
    },
    onPeerLeave: (userId: string) => {
      editorPeers.delete(userId);
      crashedPeers.delete(userId);
      // The editor we waited for left (often a ghost connection evicted by
      // the relay): open from the stored document now.
      if (otherLiveEditors().length === 0 && awaitingPeerState) {
        awaitingPeerState = false;
        binDecisionResolve?.("cold");
      }
      dropPeerLocks(userId, () => {
        removeRemoteUser(userId);
        releaseAllUserLocks(userId);
        lockArbitrator?.dropUser(userId);
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
      sendToEditor(buildConnectStateMessage() as any);
      publishStatus();
    },
    onRoomState: (
      peers: Array<{
        userId: string;
        userName: string;
        canEdit: boolean;
        joinedAt: number;
        crashed?: boolean;
      }>,
    ) => {
      editorPeers.clear();
      crashedPeers.clear();
      for (const peer of peers) {
        if (!peer.userId) continue;
        if (peer.canEdit) {
          const existing = editorPeers.get(peer.userId);
          if (existing === undefined || peer.joinedAt < existing) {
            editorPeers.set(peer.userId, peer.joinedAt);
          }
        }
        if (peer.crashed) crashedPeers.add(peer.userId);
        addRemoteUser(peer.userId, peer.userName, peer.userId);
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
      sendToEditor(buildConnectStateMessage() as any);
      // Other editors are in the room: ask for their live state, or our
      // object ids would diverge from theirs. Alone: open the stored one.
      if (otherLiveEditors().length > 0 && !outgoingSilenced) {
        awaitingPeerState = true;
        if (phase === "ready") setPhase("peer-resyncing");
        relay.sendStateRequest();
      } else {
        binDecisionResolve?.("cold");
      }
      publishStatus();
    },
    onLockUpdate: (
      type: "acquire" | "release",
      userId: string,
      lockData: unknown,
    ) => {
      const lockId = JSON.stringify(lockData);
      if (type === "acquire") acquireCellLock(lockId, userId, lockData);
      else releaseCellLock(lockId, userId);
      const remoteOOId = getRemoteOOInternalId(userId);
      const locks: Record<string, unknown> = {};
      for (const block of Array.isArray(lockData) ? lockData : [lockData]) {
        const guid = (block as { guid?: string } | null)?.guid;
        const key =
          guid || (typeof block === "string" ? block : JSON.stringify(block));
        locks[key] = {
          block,
          user: remoteOOId || userId,
          time: Date.now(),
        };
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
      whenReady(() => sendToEditor({ type: "getLock", locks } as any));
    },
    onCursorUpdate: (userId: string, cursor: unknown) => {
      const senderOOId = getRemoteOOInternalId(userId);
      if (!senderOOId) return;
      const cursorString =
        typeof cursor === "string" ? cursor : JSON.stringify(cursor);
      whenReady(() =>
        sendToEditorGuarded({
          type: "cursor",
          messages: [
            {
              cursor: cursorString,
              user: senderOOId,
              useridoriginal: senderOOId,
              time: Date.now(),
            },
          ],
        }),
      );
    },
    onMessageBroadcast: (_userId: string, messages: unknown[]) => {
      whenReady(() => sendToEditorGuarded({ type: "message", messages }));
    },
    onMetaBroadcast: (_userId: string, messages: unknown[]) => {
      whenReady(() => sendToEditorGuarded({ type: "meta", messages }));
    },
    // Saves are coordinated by leader election.
    onSaveLock: () => undefined,
    onConnectionChange: () => undefined,
    onReconnectFailed: () => {
      // Without the relay we cannot tell whether someone else edits:
      // refuse to open editable (Drive offers a read-only view instead).
      binDecisionResolve?.("no-relay");
      endPreloadPhase();
    },
    onRemoteSaveCommitted: () => {
      markRemoteSaveCommitted();
      recoveryResolve?.();
      publishStatus();
    },
    onPeerNeedsSave: () => undefined,
    onPeerCrashed: (peerUserId: string) => {
      crashedPeers.add(peerUserId);
      if (lockArbitrator) {
        dropPeerLocks(peerUserId, () => lockArbitrator?.dropUser(peerUserId));
      }
      publishStatus();
    },
    onArbitratedLockRequest: (
      peerUserId: string,
      keys: string[],
      timestampMs: number,
      blocks?: unknown[],
    ) => {
      if (!lockArbitrator) return;
      lockArbitrator.applyRemoteRequest(
        { type: "oo:lockRequest", userId: peerUserId, keys, blocks },
        timestampMs,
      );
      // Cells and shapes turn the other editor's color at once. OnlyOffice
      // reads fields of the verbatim block (sheetId, rangeType, ...): hand
      // it back as received. Word stays lazy: a paragraph may not exist
      // here yet, and announcing its lock would crash `_onGetLock`.
      if ((docType === "cell" || docType === "slide") && documentReady) {
        const peerOOId = getRemoteOOInternalId(peerUserId) ?? peerUserId;
        const locks: Record<string, unknown> = {};
        keys.forEach((key, i) => {
          locks[key] = {
            time: timestampMs,
            user: peerOOId,
            block: blocks?.[i] ?? { guid: key },
          };
          addPeerLockShownToEditor(key);
        });
        sendToEditorGuarded({ type: "getLock", locks });
      }
    },
    onArbitratedLockRelease: (peerUserId: string, keys: string[]) => {
      if (!lockArbitrator) return;
      const blockByKey = new Map<string, unknown>();
      for (const entry of lockArbitrator.snapshot()) {
        if (entry.userId === peerUserId && entry.block) {
          blockByKey.set(entry.key, entry.block);
        }
      }
      lockArbitrator.applyRemoteRelease({
        type: "oo:lockRelease",
        userId: peerUserId,
        keys,
      });
      const clearableKeys = consumePeerLocksShownToEditor(keys);
      if (documentReady && clearableKeys.length > 0) {
        const peerOOId = getRemoteOOInternalId(peerUserId) ?? peerUserId;
        sendToEditorGuarded({
          type: "releaseLock",
          locks: clearableKeys.map((key) => ({
            block:
              docType === "cell" || docType === "slide"
                ? (blockByKey.get(key) ?? { guid: key })
                : key,
            user: peerOOId,
            time: Date.now(),
          })),
        });
      }
    },
    onPeerStateRequest: (fromUserId: string) => {
      // Only the leader answers, so a joiner gets a single dump.
      if (!isSaveLeader() || outgoingSilenced || !baseBin) return;
      relay.sendStateResponse(fromUserId, baseBin, chain);
    },
    onPeerStateResponse: (
      _fromUserId: string,
      dumpBaseBin: string,
      dumpChain: Array<Record<string, unknown>>,
    ) => {
      awaitingPeerState = false;
      const dump = { baseBin: dumpBaseBin, chain: dumpChain };
      if (binDecisionResolve) {
        peerStateDump = dump;
        binDecisionResolve("peer");
      } else {
        // Already open: start again on the live state.
        requestReinit("peer-resyncing", dump);
      }
    },
    onCheckpointReload: (_fromUserId: string, dumpBaseBin: string) => {
      requestReinit("peer-resyncing", { baseBin: dumpBaseBin, chain: [] });
    },
  };

  const createEditor = (config: OOConfig): OOEditor => {
    const instance = new window.DocsAPI!.DocEditor(
      "oo-editor-placeholder",
      config,
    );
    setEditorInstance(instance);
    instance.connectMockServer(
      createMockServerCallbacks({
        docType,
        lockArbitrator: lockArbitrator ?? undefined,
        userId: user.id,
        onSaveChangesBroadcast: (message) => {
          // Installed on every change, so the very first Ctrl+Z is seen.
          try {
            installUndoFlagHook();
          } catch (e) {
            console.warn("[onlyoffice] undo hook install failed", e);
          }
          if (outgoingSilenced) return;
          relay.sendSaveChanges(message);
          chain.push(message);
          republishAfterUndo(message);
          checkpointWhenChainIsLarge();
          publishStatus();
        },
        onLockRequest: (type, lockData) => {
          if (!outgoingSilenced) relay.sendLock(type, lockData);
        },
        onCursorUpdate: (cursor) => {
          if (!outgoingSilenced) relay.sendCursor(cursor);
        },
        onMessageBroadcast: (messages) => {
          if (!outgoingSilenced) relay.sendMessage(messages);
        },
        onMetaBroadcast: (messages) => {
          if (!outgoingSilenced) relay.sendMeta(messages);
        },
        onSaveLockCheck: () => false,
        // Saving is ours (timer, closing): Cmd+S only saves in development.
        onForceSaveRequest: () => {
          if (!init.development || outgoingSilenced) return;
          forceSave().catch((e) =>
            console.warn("[onlyoffice] forceSave failed", e),
          );
        },
      }),
    );
    return instance;
  };

  // OnlyOffice's undo of a shape deletion only references the shape: an
  // editor who joined after the deletion has nothing to restore. After a
  // real Ctrl+Z producing such a tombstone, re-send the shape's transform.
  const republishAfterUndo = (message: Record<string, unknown>) => {
    const inspection = inspectOutboundForRepublish(message);
    if (
      autoRepublishGate ||
      inspection.totalBytes > 800 ||
      inspection.guids.length === 0 ||
      inspection.hasFatShapeChange
    )
      return;
    const ourJoinedAt = relayJoinedAt;
    const hasLaterPeer =
      ourJoinedAt !== null &&
      [...editorPeers.values()].some((joinedAt) => joinedAt > ourJoinedAt);
    if (!hasLaterPeer || !undoFiredRecently()) return;
    autoRepublishGate = true;
    const guids = inspection.guids;
    setTimeout(() => dispatchRepublishNudge(guids), 50);
    setTimeout(() => {
      autoRepublishGate = false;
    }, 500);
  };

  const checkpointWhenChainIsLarge = () => {
    try {
      if (!isSaveLeader()) return;
      if (JSON.stringify(chain).length <= CHECKPOINT_CHAIN_SIZE_BYTES) return;
      const win = innerWindowOf();
      const raw = (win?.editor || win?.editorCell)?.asc_nativeGetFile?.();
      const newBaseBin =
        typeof raw === "string"
          ? raw
          : raw
            ? new TextDecoder().decode(raw)
            : null;
      if (newBaseBin) relay.sendCheckpointReload(newBaseBin);
    } catch (e) {
      console.warn("[onlyoffice] checkpoint-size check threw", e);
    }
  };

  const onDocumentReady = () => {
    documentReady = true;
    installSlidePasteWorkaround();
    applyGlobalBundleWorkarounds();
    applyReadOnlyRestriction();
    // Feeding changes inside onDocumentReady lands on a half-initialised
    // model: wait for OnlyOffice's own content-ready step.
    let drained = false;
    const safeDrain = () => {
      if (drained) return;
      drained = true;
      releaseReplay();
    };
    try {
      const win = innerWindowOf();
      const innerEditor = win?.editor || win?.editorCell;
      if (
        innerEditor &&
        typeof innerEditor.onDocumentContentReady === "function" &&
        !innerEditor.__driveContentReadyHooked
      ) {
        innerEditor.__driveContentReadyHooked = true;
        const orig = innerEditor.onDocumentContentReady.bind(innerEditor);
        innerEditor.onDocumentContentReady = (...args: unknown[]) => {
          const result = orig(...args);
          safeDrain();
          return result;
        };
      } else {
        setTimeout(safeDrain, 0);
      }
    } catch (e) {
      console.warn("[onlyoffice] content-ready hook failed", e);
      setTimeout(safeDrain, 0);
    }
    setTimeout(safeDrain, 500);
    try {
      innerWindow = innerWindowOf();
      if (innerWindow) patchInnerWindow(innerWindow);
    } catch (e) {
      console.warn("[onlyoffice] failed to patch the editor frame", e);
    }
  };

  const run = async () => {
    initLocalUser(user.id, user.name);
    resetPatchIndex(0);
    resetPeerLocksShownToEditor();

    setPhase("converting");
    const converted = await convertToInternal(init.document, filename);
    const bin: Uint8Array = converted.bin;
    const extractedImages = converted.images;
    if (destroyed) return;

    // Decided before OnlyOffice starts: our own conversion, or the live
    // state of an editor already in the room.
    const binDecision = new Promise<BinDecision>((resolve) => {
      binDecisionResolve = (r) => {
        if (!binDecisionResolve) return;
        binDecisionResolve = null;
        resolve(r);
      };
      if (init.viewOnly || peerStateDump) {
        binDecisionResolve(peerStateDump ? "peer" : "cold");
        return;
      }
      setTimeout(() => {
        if (!binDecisionResolve) return;
        // A ghost tab (strict mode, hot reload) may have looked present:
        // without a real other editor left, open from the stored document.
        binDecisionResolve(
          otherLiveEditors().length === 0 ? "cold" : "no-response",
        );
      }, 15_000);
    });

    if (init.viewOnly) {
      // Nothing announced, nothing sent: a purely local view.
      endPreloadPhase();
    } else {
      lockArbitrator = new LockArbitrator({
        sendWithSettlement: (msg) => relay.sendEncryptedWithSettlement(msg),
      });
      setPhase("syncing-history");
      try {
        await bridge.call("relay.connect", []);
        relayActive = true;
      } catch (e) {
        console.warn("[onlyoffice] relay setup failed", e);
        endPreloadPhase();
        binDecisionResolve?.("no-relay");
      }
    }

    await Promise.race([
      historyReady,
      new Promise<void>((resolve) =>
        setTimeout(() => {
          endPreloadPhase();
          resolve();
        }, 120_000),
      ),
    ]);
    if (destroyed) return;

    const decision = await binDecision;
    if (destroyed) return;
    if (decision === "no-response") {
      throw Object.assign(
        new Error(
          "Another user is connected but did not respond with their live state.",
        ),
        { code: "PEER_STATE_UNAVAILABLE" },
      );
    }
    if (decision === "no-relay") {
      throw Object.assign(new Error("Cannot reach the collaboration server."), {
        code: "RELAY_UNAVAILABLE",
      });
    }

    let documentBytes: Uint8Array = bin;
    if (decision === "peer" && peerStateDump) {
      const dump = peerStateDump;
      peerStateDump = null;
      documentBytes = new TextEncoder().encode(dump.baseBin);
      baseBin = dump.baseBin;
      chain = [...dump.chain];
      for (const message of dump.chain) {
        handleIncomingSaveChanges(() => {
          observeIncomingSaveChanges(message);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
          withIncomingOTGate(() => sendToEditorGuarded(message as any));
        });
      }
    } else {
      baseBin = new TextDecoder().decode(bin);
      chain = [];
    }

    const blobUrl = URL.createObjectURL(
      new Blob([new Uint8Array(documentBytes)], {
        type: "application/octet-stream",
      }),
    );

    installAppHooks();
    const config: OOConfig = {
      document: {
        fileType: ooFileType,
        key: init.itemId + "_" + Date.now(),
        title: init.title,
        url: blobUrl,
      },
      documentType: docType,
      editorConfig: {
        // Always "edit": only an editor in a co-editing session applies
        // the others' changes live. Readers are restricted by the
        // permissions below and `asc_setRestriction`, and the relay drops
        // their frames.
        mode: "edit",
        // Must match the id in lock replies, or OnlyOffice sees our own
        // locks as someone else's.
        user: { id: getUniqueOOId(), name: user.name },
        lang: user.language || "en",
        // Our relay carries per-keystroke changes: strict mode's
        // paragraph locks need a real Document Server.
        coEditing: { mode: "fast", change: false },
        customization: {
          compactToolbar: false,
          forcesave: init.development,
          // Drives the timer that ships changes to the other editors.
          autosave: true,
          macros: false,
          plugins: false,
          help: false,
          chat: true,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
        } as any,
        permissions: {
          edit: canEdit,
          comment: canEdit,
          review: canEdit,
          fillForms: canEdit,
          modifyContentControl: canEdit,
          modifyFilter: canEdit,
          copy: canEdit,
          chat: true,
          deleteCommentAuthorOnly: false,
          editCommentAuthorOnly: false,
          macros: "none",
          protect: false,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
        } as any,
      },
      events: {
        // Images resolve through g_oDocumentUrls while the document
        // loads: register them first.
        onAppReady: () => {
          try {
            const docUrls = innerWindowOf()?.AscCommon?.g_oDocumentUrls;
            if (!docUrls) return;
            for (const img of extractedImages) {
              try {
                // Data URLs stay valid when copied into another tab.
                docUrls.addImageUrl(
                  img.name,
                  bytesToDataUrl(img.data, imageMime(img.name)),
                );
              } catch (e) {
                console.warn(
                  "[onlyoffice] failed to register image",
                  img.name,
                  e,
                );
              }
            }
            for (const [name, url] of Object.entries(historyInitialMedia)) {
              docUrls.addImageUrl(name, url);
            }
          } catch (e) {
            console.warn("[onlyoffice] image registration failed", e);
          }
        },
        onDocumentReady,
        onError: (event: {
          data?: { errorCode?: unknown; errorDescription?: unknown };
        }) => {
          console.error("[onlyoffice] OnlyOffice error:", event.data);
          const { errorCode, errorDescription } = event.data ?? {};
          bridge.emit({
            type: "failure",
            code: null,
            message:
              `OnlyOffice error ${String(errorCode)}: ${String(errorDescription)}`.slice(
                0,
                2000,
              ),
          });
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- OnlyOffice editor bundle boundary
      } as any,
    };

    if (!window.DocsAPI) throw new Error("OnlyOffice API not loaded");
    editor = createEditor(config);

    if (canEdit) {
      initCheckpointing({
        editor,
        format: x2tExtension,
        type: x2tType,
        userId: user.id,
        onUpload: async (content, format) => {
          await bridge.call("upload", [content, format], [content]);
        },
        isSaveLeader,
        onSaveResult: (result) => {
          bridge.emit({ type: "save-result", result });
          publishStatus();
        },
      });
    }
  };

  void run().catch((err) => {
    if (destroyed) return;
    console.error("[onlyoffice] editor failed to start", err);
    const code = (err as { code?: unknown })?.code;
    bridge.emit({
      type: "failure",
      code: typeof code === "string" ? code : null,
      message: (err instanceof Error ? err.message : String(err)).slice(
        0,
        2000,
      ),
    });
  });

  return {
    onRelayEvent: (name, args, joinedAt) => {
      if (destroyed) return;
      relayJoinedAt = joinedAt;
      const handler = relayCallbacks[name] as (...a: unknown[]) => void;
      try {
        handler(...args);
      } catch (e) {
        console.warn(`[onlyoffice] relay event ${name} failed`, e);
      }
    },
    command: async (name) => {
      if (name === "forceSave") {
        await forceSave();
        publishStatus();
      } else if (name === "recover") {
        await requestRecoveryReload();
      }
    },
    destroy: () => {
      destroyed = true;
      clearInterval(statusTimer);
      window.removeEventListener("error", handleOOError);
      stopCheckpointing();
      resetAllLocks();
      try {
        editor?.destroyEditor();
      } catch {
        // Already gone with its frame.
      }
      editor = null;
      setEditorInstance(null);
    },
  };
}
