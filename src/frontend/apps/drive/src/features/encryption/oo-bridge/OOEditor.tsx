/**
 * OnlyOffice editor for encrypted documents.
 *
 * OnlyOffice runs in the OnlyOffice sandbox: a page on its own origin
 * (`ENCRYPTION_ONLYOFFICE_SANDBOX_URL`), framed here, that only ever receives
 * the plaintext of this document. A flaw in OnlyOffice or x2t exploited by
 * a booby-trapped file therefore reaches neither the session, nor the vault,
 * nor the other files: Drive keeps decrypting, encrypting, uploading and the
 * encrypted relay, and answers the sandbox only through the messages of
 * `oo-sandbox/protocol.ts`, each one checked before it acts.
 *
 * Flow: decrypt here, hand the bytes to the sandbox, which converts and
 * edits them, relay its changes encrypted to the other editors, and encrypt
 * and upload what it saves.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Button,
  Loader,
  VariantType,
} from "@gouvfr-lasuite/ui-components";
import {
  Download,
  Eye,
  PlugOff,
  Retry,
  Unlock,
} from "@gouvfr-lasuite/ui-components/icons";
import { Item } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import { useConfig } from "@/features/config/ConfigProvider";
import { fetchAPI } from "@/features/api/fetchApi";
import { errorToCode } from "@/features/api/APIError";
import { getEffectiveMimetype } from "@/features/explorer/utils/mimeTypes";
import {
  DecryptionFailurePanel,
  decryptionFailureOf,
} from "@/features/encryption/DecryptionFailurePanel";
import { EncryptionState } from "@/features/encryption/EncryptionLayout";
import { MissingEncryptionKeysPanel } from "@/features/encryption/MissingEncryptionKeysModal";
import { useVaultClient } from "@/features/encryption/VaultClientProvider";
import { useAuth } from "@/features/auth/Auth";
import { downloadDecryptedFile } from "@/features/items/hooks/useDecryptedContent";
import { ModalRecursiveRemoveEncryption } from "@/features/encryption/ModalRecursiveRemoveEncryption";
import { backfillMaintenanceCopy } from "@/features/encryption/maintenanceEscrow";
import {
  EXPORT_MIME_BY_EXTENSION,
  ONLYOFFICE_SANDBOX_PROTOCOL,
  RELAY_EVENTS,
  SANDBOX_CONNECT,
  exportFileName,
  parseSandboxMessage,
  type EnginePhase,
  type HostToSandbox,
  type PeerStateDump,
  type SandboxCommand,
  type SandboxToHost,
} from "@/features/encryption/oo-sandbox/protocol";
import { EncryptedRelay, type RelayCallbacks } from "./encryptedRelay";
import { MIME_TO_EXTENSION } from "./types";
import styles from "./OOEditor.module.scss";

interface OOEditorProps {
  item: Item;
}

type EditorState =
  | EnginePhase
  | "decrypting"
  /** Reloading from the stored document after a long disconnection or a crash. */
  | "stale-resyncing"
  | "error";

/** How long the sandbox may take to load OnlyOffice before we give up. */
const SANDBOX_READY_TIMEOUT_MS = 60_000;
/** How long closing waits for the last save. */
const CLOSE_SAVE_TIMEOUT_MS = 30_000;

// The sandbox needs scripts and its own origin (OnlyOffice's frames, workers
// and storage). It may neither navigate this page, nor open windows, nor
// submit forms. `credentialless`, where supported, also keeps every cookie
// of this site away from it.
const SANDBOX_FLAGS = "allow-scripts allow-same-origin allow-modals";

// A frame may always navigate itself, whatever its own policy says: the
// sandbox is framed through this empty page, whose policy lets its frame
// load the sandbox's origin only, so a navigation elsewhere carrying the
// document is refused before any request leaves.
const wrapperDocument = (sandboxOrigin: string) =>
  `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; frame-src ${sandboxOrigin}"><style>html,body,iframe{display:block;width:100%;height:100%;margin:0;border:0;overflow:hidden}</style></head><body></body></html>`;

const toBuffer = (base64: string): ArrayBuffer => {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
};

/** Print a PDF the sandbox exported, from this page. */
const printPdf = (url: string) => {
  document.getElementById("drive-print-iframe")?.remove();
  const iframe = document.createElement("iframe");
  iframe.id = "drive-print-iframe";
  Object.assign(iframe.style, {
    position: "fixed",
    right: "0",
    bottom: "0",
    width: "0",
    height: "0",
    border: "0",
  });
  iframe.onload = () => {
    try {
      iframe.contentWindow?.focus();
      iframe.contentWindow?.print();
    } catch (e) {
      console.error("[OOEditor] print failed, opening a tab", e);
      window.open(url, "_blank", "noopener");
    }
  };
  iframe.src = url;
  document.body.appendChild(iframe);
};

const download = (url: string, name: string) => {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.rel = "noopener";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
};

export const OOEditor = ({ item }: OOEditorProps) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { config } = useConfig();
  const { hasKeys, openEncryptionOnboarding } = useVaultClient();
  // Must match the ACL signed in the presigned upload URL; none when the
  // backend lets the bucket default apply.
  const uploadAcl =
    config.AWS_S3_UPLOAD_ACL === "default"
      ? undefined
      : config.AWS_S3_UPLOAD_ACL;
  const sandboxUrl = config.ENCRYPTION_ONLYOFFICE_SANDBOX_URL ?? null;
  const [state, setState] = useState<EditorState>("loading");
  // Only Drive's own messages: the sandbox's are logged, never shown.
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [showRemoveEncryption, setShowRemoveEncryption] = useState(false);
  const [downloading, setDownloading] = useState(false);
  // Banner over a running editor: `fatal` when x2t refuses the document
  // (retrying cannot help), `transient` for a network or vault hiccup.
  const [saveError, setSaveError] = useState<"fatal" | "transient" | null>(
    null,
  );
  const [saveRetrying, setSaveRetrying] = useState(false);
  const [relayFailed, setRelayFailed] = useState(false);
  const [recoveryWaiting, setRecoveryWaiting] = useState(false);
  // Bumped to start again: a fresh sandbox, a fresh download.
  const [reinitKey, setReinitKey] = useState(0);
  // Open locally, read-only and without the relay, when joining the live
  // session failed: nothing is sent to the room.
  const [viewOnlyOverride, setViewOnlyOverride] = useState(false);
  const [flushingOnClose, setFlushingOnClose] = useState(false);
  const frameHostRef = useRef<HTMLDivElement>(null);
  // Live state an editor shipped us, kept across the restart it triggers.
  const peerStateRef = useRef<PeerStateDump | null>(null);
  // What the sandbox last said: we are the editor responsible for saving
  // and changes are not saved yet. Read synchronously when the tab closes.
  const unsavedAsLeaderRef = useRef(false);
  const commandRef = useRef<
    ((name: SandboxCommand, timeoutMs?: number) => Promise<void>) | null
  >(null);

  const canEdit = !!item.abilities?.partial_update && !viewOnlyOverride;
  // Encrypted files are stored as `application/octet-stream`: the effective
  // type comes from the extension.
  const mimetype = getEffectiveMimetype(item) || "";
  const x2tExtension = MIME_TO_EXTENSION[mimetype] || "docx";

  const sendCommand = useCallback(
    (name: SandboxCommand, timeoutMs?: number): Promise<void> =>
      commandRef.current?.(name, timeoutMs) ?? Promise.resolve(),
    [],
  );
  const forceSave = useCallback(() => sendCommand("forceSave"), [sendCommand]);
  const requestRecoveryReload = useCallback(() => {
    void sendCommand("recover").catch((e) =>
      console.warn("[OOEditor] recovery request failed", e),
    );
  }, [sendCommand]);

  const restart = (viewOnly: boolean) => {
    setViewOnlyOverride(viewOnly);
    peerStateRef.current = null;
    setError(null);
    setErrorCode(null);
    setState("loading");
    setReinitKey((k) => k + 1);
  };

  const uploadEncrypted = useCallback(
    async (content: ArrayBuffer): Promise<void> => {
      const vaultClient = window.__driveVaultClient;
      if (!vaultClient) throw new Error("Vault client not available");
      const keyChain = await getDriver().getKeyChain(item.id);
      const encryptedKeyChain = keyChain.chain.map((entry) =>
        toBuffer(entry.encrypted_symmetric_key),
      );
      // The document is discarded after this call: let the vault take it.
      const { encryptedData } = await vaultClient.encryptWithKey(
        content,
        toBuffer(keyChain.encrypted_key_for_user),
        encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined,
        { optimizeMemory: true },
      );

      // The current key: S3 versioning keeps the previous contents.
      let urlResponse: Response;
      try {
        urlResponse = await fetchAPI(
          `items/${item.id}/encryption-upload-url/`,
          {
            method: "POST",
            body: JSON.stringify({ size: encryptedData.byteLength }),
            headers: { "Content-Type": "application/json" },
          },
          { redirectOn40x: false },
        );
      } catch (error) {
        // Back to plaintext while open: this save would write ciphertext
        // nothing reads any more.
        if (errorToCode(error) === "item_not_encrypted") {
          throw new Error(
            t(
              "explorer.encrypted.save_error_not_encrypted",
              "This file is no longer encrypted. Close it and open it again to keep editing: the latest changes were not saved.",
            ),
          );
        }
        throw error;
      }
      const { upload_url: uploadUrl } = await urlResponse.json();

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", uploadUrl);
        if (uploadAcl) xhr.setRequestHeader("X-amz-acl", uploadAcl);
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
        xhr.addEventListener("error", () =>
          reject(new Error("S3 upload network error")),
        );
        xhr.addEventListener("abort", () =>
          reject(new Error("S3 upload aborted")),
        );
        xhr.addEventListener("readystatechange", () => {
          if (xhr.readyState !== 4) return;
          if (xhr.status === 200) resolve();
          else
            reject(
              new Error(
                `S3 upload failed: ${xhr.status} ${xhr.responseText.slice(0, 200)}`,
              ),
            );
        });
        xhr.send(new Uint8Array(encryptedData));
      });
    },
    [item.id, uploadAcl, t],
  );

  /**
   * The preview's close button awaits this before unmounting the editor:
   * the last save must run while the sandbox is still there.
   */
  useEffect(() => {
    const guard = async (): Promise<void> => {
      if (!unsavedAsLeaderRef.current) return;
      setFlushingOnClose(true);
      try {
        await forceSave();
      } catch (e) {
        console.error("[OOEditor] flush-on-close save failed", e);
      } finally {
        setFlushingOnClose(false);
      }
    };
    const w = window as unknown as {
      __driveOOEditorSaveGuard?: () => Promise<void>;
    };
    w.__driveOOEditorSaveGuard = guard;
    return () => {
      if (w.__driveOOEditorSaveGuard === guard) {
        delete w.__driveOOEditorSaveGuard;
      }
    };
  }, [forceSave]);

  useEffect(() => {
    let cancelled = false;
    // Once failed, the sandbox is not listened to any more: its engine may
    // still run, but the error screen stays until the user starts again.
    let failed = false;
    let relay: EncryptedRelay | null = null;
    let wrapper: HTMLIFrameElement | null = null;
    let readyTimer: ReturnType<typeof setTimeout> | undefined;
    const channel = new MessageChannel();
    const port = channel.port1;
    let nextCommandId = 1;
    const pendingCommands = new Map<
      number,
      { resolve: () => void; reject: (error: Error) => void }
    >();
    let resolveReady: () => void = () => {};
    let rejectReady: (error: Error) => void = () => {};
    const sandboxReady = new Promise<void>((resolve, reject) => {
      resolveReady = resolve;
      rejectReady = reject;
    });
    // Awaited only once the document is decrypted: may fail before that.
    sandboxReady.catch(() => undefined);

    const fail = (message: string | null, code: string | null) => {
      if (cancelled || failed) return;
      failed = true;
      setError(message);
      setErrorCode(code);
      setState("error");
    };

    const send = (message: HostToSandbox, transfer: Transferable[] = []) => {
      if (!cancelled) port.postMessage(message, transfer);
    };

    commandRef.current = (name, timeoutMs = CLOSE_SAVE_TIMEOUT_MS) =>
      new Promise<void>((resolve, reject) => {
        const id = nextCommandId++;
        const timer = setTimeout(() => {
          pendingCommands.delete(id);
          reject(new Error(`${name} timed out`));
        }, timeoutMs);
        pendingCommands.set(id, {
          resolve: () => {
            clearTimeout(timer);
            resolve();
          },
          reject: (error) => {
            clearTimeout(timer);
            reject(error);
          },
        });
        send({ type: "command", id, name });
      });

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // Only the editor responsible for saving has anything to lose.
      if (unsavedAsLeaderRef.current) e.preventDefault();
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden" && unsavedAsLeaderRef.current) {
        void commandRef.current?.("forceSave").catch(() => undefined);
      }
    };

    // The room's traffic, encrypted and decrypted here, passed through to
    // the sandbox by callback name.
    const connectRelay = (keys: {
      entryKey: ArrayBuffer;
      chain: ArrayBuffer[];
      version: number;
    }) => {
      const vaultClient = window.__driveVaultClient;
      if (!vaultClient || !user?.sub) throw new Error("Vault client not ready");
      const callbacks = Object.fromEntries(
        RELAY_EVENTS.map((name) => [
          name,
          (...args: unknown[]) => {
            if (name === "onConnectionChange" && args[0]) {
              setRelayFailed(false);
            }
            if (name === "onReconnectFailed") setRelayFailed(true);
            send({
              type: "relay:event",
              name,
              args,
              joinedAt: relay?.joinedAt ?? null,
            });
          },
        ]),
      ) as unknown as RelayCallbacks;
      relay = new EncryptedRelay({
        roomId: item.id,
        userId: user.sub,
        userName: user.full_name || user.email,
        vaultClient,
        encryptedSymmetricKey: keys.entryKey,
        encryptedKeyChain: keys.chain,
        keyVersion: keys.version,
        callbacks,
      });
      relay.connect();
    };

    const handleRpc = async (
      message: Extract<SandboxToHost, { type: "rpc" }>,
      keys: { entryKey: ArrayBuffer; chain: ArrayBuffer[]; version: number },
    ): Promise<unknown> => {
      if (cancelled) throw new Error("editor closed");
      const { method, args } = message;
      if (method === "relay.connect") {
        // What the sandbox was told it may do, enforced here.
        if (viewOnlyOverride) throw new Error("view only");
        if (relay) throw new Error("relay already connected");
        connectRelay(keys);
        return undefined;
      }
      if (method === "upload") {
        if (!canEdit) throw new Error("read only");
        await uploadEncrypted(args[0] as ArrayBuffer);
        relay?.sendSaveCommitted();
        return undefined;
      }
      if (!relay) throw new Error("relay not connected");
      switch (method) {
        case "relay.sendSaveChanges":
          return relay.sendSaveChanges(args[0] as Record<string, unknown>);
        case "relay.sendLock":
          return relay.sendLock(args[0] as "acquire" | "release", args[1]);
        case "relay.sendCursor":
          return relay.sendCursor(args[0]);
        case "relay.sendMessage":
          return relay.sendMessage(args[0] as unknown[]);
        case "relay.sendMeta":
          return relay.sendMeta(args[0] as unknown[]);
        case "relay.sendCrashed":
          return relay.sendCrashed();
        case "relay.sendStateRequest":
          return relay.sendStateRequest();
        case "relay.sendStateResponse":
          return relay.sendStateResponse(
            args[0] as string,
            args[1] as string,
            args[2] as Array<Record<string, unknown>>,
          );
        case "relay.sendCheckpointReload":
          return relay.sendCheckpointReload(args[0] as string);
        case "relay.sendEncryptedWithSettlement":
          return relay.sendEncryptedWithSettlement(args[0] as object);
        case "relay.queuePendingMedia":
          return relay.queuePendingMedia(args[0] as string, args[1] as string);
      }
    };

    const handleExport = (
      message: Extract<SandboxToHost, { type: "export" }>,
    ) => {
      const url = URL.createObjectURL(
        new Blob([message.bytes], {
          type: EXPORT_MIME_BY_EXTENSION[message.extension],
        }),
      );
      if (message.mode === "print") printPdf(url);
      else download(url, exportFileName(message.title, message.extension));
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    };

    const listen = (
      keys: Promise<{
        entryKey: ArrayBuffer;
        chain: ArrayBuffer[];
        version: number;
      }>,
    ) => {
      port.onmessage = (event: MessageEvent) => {
        if (cancelled || failed) return;
        const message = parseSandboxMessage(event.data);
        if (!message) {
          console.warn("[OOEditor] dropped an invalid sandbox message");
          return;
        }
        switch (message.type) {
          case "ready":
            resolveReady();
            return;
          case "phase":
            setState(message.phase);
            return;
          case "failure":
            console.error("[OOEditor] the editor failed:", message.message);
            rejectReady(new Error(message.message));
            fail(null, message.code);
            return;
          case "reinit":
            peerStateRef.current = message.peerState;
            setState(message.phase);
            setReinitKey((k) => k + 1);
            return;
          case "save-result":
            if (message.result) {
              console.warn("[OOEditor] save failed:", message.result.detail);
            }
            setSaveError(message.result?.kind ?? null);
            if (!message.result) setSaveRetrying(false);
            return;
          case "status":
            unsavedAsLeaderRef.current = message.unsavedAsLeader;
            return;
          case "recovery":
            setRecoveryWaiting(message.waiting);
            return;
          case "rpc":
            void keys
              .then((k) => handleRpc(message, k))
              .then((value) =>
                send({
                  type: "rpc:result",
                  id: message.id,
                  ok: true,
                  value: typeof value === "number" ? value : undefined,
                }),
              )
              .catch((error) =>
                send({
                  type: "rpc:result",
                  id: message.id,
                  ok: false,
                  error: error instanceof Error ? error.message : String(error),
                }),
              );
            return;
          case "export":
            handleExport(message);
            return;
          case "command:result": {
            const pending = pendingCommands.get(message.id);
            if (!pending) return;
            pendingCommands.delete(message.id);
            if (message.ok) pending.resolve();
            else pending.reject(new Error(message.error ?? "command failed"));
            return;
          }
        }
      };
    };

    const mountSandbox = (sandboxUrl: string, sandboxOrigin: string) => {
      wrapper = document.createElement("iframe");
      wrapper.title = item.title;
      wrapper.className = styles.sandboxFrame;
      wrapper.setAttribute("allow", "clipboard-write");
      wrapper.srcdoc = wrapperDocument(sandboxOrigin);
      wrapper.addEventListener(
        "load",
        () => {
          const doc = wrapper?.contentDocument;
          if (cancelled || !doc) return;
          const frame = doc.createElement("iframe");
          frame.title = item.title;
          frame.setAttribute("sandbox", SANDBOX_FLAGS);
          frame.setAttribute("allow", "clipboard-write");
          frame.setAttribute("credentialless", "");
          frame.referrerPolicy = "no-referrer";
          let loaded = false;
          frame.addEventListener("load", () => {
            if (cancelled || !frame.contentWindow) return;
            if (loaded) {
              // The sandbox navigated away: whatever runs there now gets
              // nothing more from us.
              port.close();
              fail(null, null);
              return;
            }
            loaded = true;
            frame.contentWindow.postMessage(
              { type: SANDBOX_CONNECT, protocol: ONLYOFFICE_SANDBOX_PROTOCOL },
              sandboxOrigin,
              [channel.port2],
            );
          });
          frame.src = sandboxUrl;
          doc.body.appendChild(frame);
        },
        { once: true },
      );
      frameHostRef.current?.appendChild(wrapper);
    };

    const init = async () => {
      try {
        if (!item.url || !user?.sub) return;
        unsavedAsLeaderRef.current = false;
        setRecoveryWaiting(false);

        // Without its own origin, the editor would run with this page's
        // rights: refuse rather than fall back.
        const sandboxOrigin = sandboxUrl ? new URL(sandboxUrl).origin : null;
        if (
          !sandboxUrl ||
          !sandboxOrigin ||
          sandboxOrigin === window.location.origin
        ) {
          throw Object.assign(
            new Error(
              t(
                "explorer.encrypted.onlyoffice_unavailable",
                "Encrypted documents cannot be opened in the editor on this server. Download the file to read it.",
              ),
            ),
            { code: "ONLYOFFICE_SANDBOX_UNAVAILABLE" },
          );
        }

        setState("loading");

        // The keys are read once: decrypting, then the relay.
        const keyChainPromise = getDriver().getKeyChain(item.id);
        const keys = keyChainPromise.then((keyChain) => ({
          entryKey: toBuffer(keyChain.encrypted_key_for_user),
          chain: keyChain.chain.map((entry) =>
            toBuffer(entry.encrypted_symmetric_key),
          ),
          version: keyChain.encryption_public_key_version ?? 1,
        }));
        keys.catch(() => undefined);
        listen(keys);
        mountSandbox(sandboxUrl, sandboxOrigin);

        readyTimer = setTimeout(
          () => rejectReady(new Error("The editor took too long to load.")),
          SANDBOX_READY_TIMEOUT_MS,
        );

        setState("decrypting");
        const keyChain = await keyChainPromise;
        void backfillMaintenanceCopy(keyChain);
        const response = await fetch(item.url, {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
        const encryptedBuffer = await response.arrayBuffer();
        const vaultClient = window.__driveVaultClient;
        if (!vaultClient) throw new Error("Vault client not initialized");
        const { entryKey, chain, version } = await keys;
        const { data: decryptedBuffer } = await vaultClient.decryptWithKey(
          encryptedBuffer,
          entryKey,
          version,
          chain.length > 0 ? chain : undefined,
          { optimizeMemory: true },
        );
        if (cancelled) return;

        await sandboxReady;
        clearTimeout(readyTimer);
        if (cancelled) return;

        const peerState = peerStateRef.current;
        peerStateRef.current = null;
        send(
          {
            type: "init",
            init: {
              protocol: ONLYOFFICE_SANDBOX_PROTOCOL,
              itemId: item.id,
              title: item.title,
              mimetype,
              document: decryptedBuffer,
              user: {
                id: user.sub,
                name: user.full_name || user.email,
                language: user.language || "en",
              },
              canEdit,
              viewOnly: viewOnlyOverride,
              peerState,
              development: process.env.NODE_ENV === "development",
            },
          },
          [decryptedBuffer],
        );

        window.addEventListener("beforeunload", handleBeforeUnload);
        document.addEventListener("visibilitychange", handleVisibilityChange);
      } catch (err) {
        if (cancelled) return;
        console.error("OOEditor init failed:", err);
        const code = (err as { code?: unknown })?.code;
        fail(
          err instanceof Error ? err.message : null,
          typeof code === "string" ? code : null,
        );
      }
    };

    void init();

    return () => {
      cancelled = true;
      clearTimeout(readyTimer);
      commandRef.current = null;
      window.removeEventListener("beforeunload", handleBeforeUnload);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      for (const pending of pendingCommands.values()) {
        pending.reject(new Error("editor closed"));
      }
      port.close();
      relay?.destroy();
      wrapper?.remove();
    };
    // `canEdit`, `mimetype` and `viewOnlyOverride` change with `reinitKey`.
  }, [item.id, reinitKey]);

  // Keys enabled from the panel below: open the document again with them.
  useEffect(() => {
    if (state !== "error" || errorCode !== "MISSING_KEYS" || !hasKeys) return;
    setError(null);
    setErrorCode(null);
    setState("loading");
    setReinitKey((k) => k + 1);
  }, [state, errorCode, hasKeys]);

  if (state === "error") {
    // A key that cannot open the file, or content that fails its integrity
    // check, gets the same explanation as the non-office viewer; the other
    // failures keep this screen and its escape hatches.
    const failure = decryptionFailureOf(errorCode);
    if (failure !== "unknown") {
      return <DecryptionFailurePanel failure={failure} />;
    }
    if (errorCode === "MISSING_KEYS") {
      return <MissingEncryptionKeysPanel onSetUp={openEncryptionOnboarding} />;
    }

    const isConversionError = errorCode === "CONVERSION_FAILED";
    const isPeerStateUnavailable = errorCode === "PEER_STATE_UNAVAILABLE";
    const isRelayUnavailable = errorCode === "RELAY_UNAVAILABLE";
    // Both offer to try again or to open read-only.
    const isUnsafeToOpen = isPeerStateUnavailable || isRelayUnavailable;
    const isSandboxUnavailable = errorCode === "ONLYOFFICE_SANDBOX_UNAVAILABLE";
    const isOdfFormat = ["odt", "ods", "odp"].includes(x2tExtension);
    const canEditItem = !!item.abilities?.partial_update;
    const canRemoveEncryption = !!item.abilities?.remove_encryption;

    const title = isRelayUnavailable
      ? t(
          "explorer.encrypted.relay_unavailable_headline",
          "Could not reach the collaboration server",
        )
      : isPeerStateUnavailable
        ? t(
            "explorer.encrypted.peer_state_unavailable_headline",
            "Could not synchronise with the active editor",
          )
        : t("explorer.encrypted.editor_error", "Failed to load editor");

    let description: string | null;
    if (isRelayUnavailable) {
      description = t(
        "explorer.encrypted.relay_unavailable_body",
        "We couldn't connect to the collaboration server, so we can't tell whether someone else is currently editing this document. Opening it anyway could overwrite their changes. Please check your network and try again in a few moments, or contact support if the problem persists.",
      );
    } else if (isPeerStateUnavailable) {
      description = t(
        "explorer.encrypted.peer_state_unavailable_body",
        "Another user is already editing this document. We tried to fetch their live state to join the session safely, but they didn't respond. Opening the document anyway could corrupt it. Please try again in a few moments, or contact support if the problem persists.",
      );
    } else if (isConversionError) {
      description = isOdfFormat
        ? null
        : canEditItem
          ? t(
              "explorer.encrypted.conversion_unexpected",
              "This error is unexpected for this file format. You can download the file to inspect it, or try removing encryption: the full-featured editor may be able to open it. If removing encryption works, please contact the technical team so they can investigate why the encrypted editor failed.",
            )
          : t(
              "explorer.encrypted.conversion_unexpected_no_edit",
              "Please contact the owner of this document or a user with editing rights to investigate.",
            );
    } else {
      description =
        error ??
        t(
          "explorer.encrypted.editor_error_body",
          "Try again in a moment. If it keeps failing, download the file to read it.",
        );
    }

    const downloadButton = (
      <Button
        size="small"
        variant="secondary"
        disabled={downloading}
        icon={<Download aria-hidden />}
        onClick={async () => {
          setDownloading(true);
          try {
            await downloadDecryptedFile(item);
          } catch (e) {
            console.error("[OOEditor] download decrypted failed", e);
          } finally {
            setDownloading(false);
          }
        }}
      >
        {downloading
          ? t("explorer.encrypted.downloading", "Downloading...")
          : t("explorer.encrypted.download_to_inspect", "Download file")}
      </Button>
    );

    let actions;
    if (isUnsafeToOpen) {
      actions = (
        <>
          <Button
            size="small"
            icon={<Retry aria-hidden />}
            onClick={() => restart(false)}
          >
            {t("explorer.encrypted.peer_state_unavailable_retry", "Try again")}
          </Button>
          <Button
            size="small"
            variant="secondary"
            icon={<Eye aria-hidden />}
            onClick={() => restart(true)}
          >
            {t(
              "explorer.encrypted.peer_state_unavailable_view_only",
              "Open in read-only",
            )}
          </Button>
        </>
      );
    } else if (isConversionError) {
      actions = canEditItem ? (
        <>
          {downloadButton}
          {canRemoveEncryption && (
            <Button
              size="small"
              icon={<Unlock aria-hidden />}
              onClick={() => setShowRemoveEncryption(true)}
            >
              {t("explorer.encrypted.remove_encryption", "Remove encryption")}
            </Button>
          )}
        </>
      ) : undefined;
    } else if (isSandboxUnavailable) {
      actions = downloadButton;
    } else {
      actions = (
        <>
          <Button
            size="small"
            icon={<Retry aria-hidden />}
            onClick={() => restart(viewOnlyOverride)}
          >
            {t("explorer.encrypted.peer_state_unavailable_retry", "Try again")}
          </Button>
          {downloadButton}
        </>
      );
    }

    return (
      <>
        <EncryptionState
          title={title}
          description={description}
          actions={actions}
        >
          {isConversionError && isOdfFormat && (
            <div className={styles.hint}>
              <Alert type={VariantType.WARNING}>
                <div>
                  <strong className={styles.hintTitle}>
                    {t(
                      "explorer.encrypted.conversion_hint_title",
                      "Why does this happen?",
                    )}
                  </strong>
                  <p className={styles.hintText}>
                    {t(
                      "explorer.encrypted.conversion_odf_body",
                      "Encrypted documents are opened with a lightweight browser-based editor that does not support all features available in non-encrypted mode. SmartArt elements and some shapes (e.g. Frame, Snip diagonal corner rectangle, math operators, most figured arrows, trapezoid, parallelogram, plus) are known to prevent ODF files (.odt, .ods, .odp) from loading in this mode.",
                    )}
                  </p>
                  <p className={styles.hintText}>
                    {canEditItem
                      ? t(
                          "explorer.encrypted.conversion_odf_actions",
                          "You can download the file to remove the SmartArt or unsupported shapes, then re-upload it. Alternatively, you can remove encryption from this document so it opens with the full-featured editor. If the issue persists after the cleanup, please contact the technical team to investigate.",
                        )
                      : t(
                          "explorer.encrypted.conversion_odf_no_edit",
                          "Please contact the owner of this document or a user with editing rights so they can remove the SmartArt, unsupported shapes, or encryption from the file. If the issue persists after the cleanup, please contact the technical team to investigate.",
                        )}
                  </p>
                </div>
              </Alert>
            </div>
          )}
        </EncryptionState>
        {showRemoveEncryption && (
          <ModalRecursiveRemoveEncryption
            isOpen={showRemoveEncryption}
            onClose={() => setShowRemoveEncryption(false)}
            item={item}
          />
        )}
      </>
    );
  }

  return (
    <div className={styles.ooEditorContainer}>
      {/* Above the editor, which shrinks: its toolbar stays usable. */}
      {saveError && state !== "oo-crashed" && (
        <div className={styles.saveError}>
          <Alert
            type={
              saveError === "fatal" ? VariantType.ERROR : VariantType.WARNING
            }
            buttons={
              saveError === "transient" ? (
                <Button
                  size="small"
                  variant="tertiary"
                  disabled={saveRetrying}
                  onClick={async () => {
                    setSaveRetrying(true);
                    try {
                      await forceSave();
                    } catch {
                      // The next save result updates the banner.
                    } finally {
                      setSaveRetrying(false);
                    }
                  }}
                >
                  {saveRetrying
                    ? t("explorer.encrypted.save_error_retrying", "Retrying…")
                    : t("explorer.encrypted.save_error_retry", "Retry now")}
                </Button>
              ) : undefined
            }
          >
            <div>
              <strong className={styles.hintTitle}>
                {saveError === "fatal"
                  ? t(
                      "explorer.encrypted.save_error_fatal_title",
                      "Saving failed, please contact support",
                    )
                  : t(
                      "explorer.encrypted.save_error_transient_title",
                      "Sync error, the save will be retried",
                    )}
              </strong>
              <p className={styles.hintText}>
                {saveError === "fatal"
                  ? t(
                      "explorer.encrypted.save_error_fatal_body",
                      "The document contains content we cannot serialize to the on-disk format (often a chart). Your recent edits are visible but unsaved. Please undo the last change or contact support.",
                    )
                  : t(
                      "explorer.encrypted.save_error_transient_body",
                      "We could not upload the latest save.",
                    )}
              </p>
            </div>
          </Alert>
        </div>
      )}
      <div className={styles.editorArea}>
        {/* The sandbox's iframe goes here. */}
        <div ref={frameHostRef} className={styles.frameHost} />
        {state !== "ready" && state !== "oo-crashed" && (
          <div className={styles.overlay}>
            <Loader />
            <span className={styles.overlayText}>
              {state === "decrypting" &&
                t("explorer.encrypted.decrypting", "Decrypting...")}
              {state === "converting" &&
                t("explorer.encrypted.converting", "Preparing editor...")}
              {state === "syncing-history" &&
                t(
                  "explorer.encrypted.syncing_history",
                  "Syncing collaborative state...",
                )}
              {state === "stale-resyncing" &&
                t(
                  "explorer.encrypted.stale_resyncing",
                  "Reconnecting after long disconnect, refetching document...",
                )}
              {state === "peer-resyncing" &&
                t(
                  "explorer.encrypted.peer_resyncing",
                  "A co-editor is resyncing, holding on for a moment...",
                )}
              {state === "loading" &&
                t("explorer.encrypted.loading_editor", "Loading editor...")}
            </span>
          </div>
        )}
        {/* The last save, awaited by the preview's close button. */}
        {flushingOnClose && (
          <div className={`${styles.overlay} ${styles.overlayTop}`}>
            <Loader />
            <span className={styles.overlayText}>
              {t(
                "explorer.encrypted.flushing_on_close",
                "Saving your changes before closing…",
              )}
            </span>
          </div>
        )}
        {state === "oo-crashed" && (
          <div className={`${styles.overlay} ${styles.overlayTop}`}>
            <EncryptionState
              title={t(
                "explorer.encrypted.oo_crashed_title",
                "Synchronization error",
              )}
              description={t(
                "explorer.encrypted.oo_crashed_body",
                "An error occurred while synchronizing with other peers. Because the document is end-to-end encrypted, we cannot always reconcile changes perfectly. Please reload the editor to fetch the latest saved state.",
              )}
              actions={
                <Button
                  size="small"
                  disabled={recoveryWaiting}
                  icon={recoveryWaiting ? undefined : <Retry aria-hidden />}
                  onClick={requestRecoveryReload}
                >
                  {recoveryWaiting
                    ? t(
                        "explorer.encrypted.oo_crashed_waiting",
                        "Waiting for peers to save…",
                      )
                    : t(
                        "explorer.encrypted.oo_crashed_reload",
                        "Reload editor",
                      )}
                </Button>
              }
            />
          </div>
        )}
      </div>
      {relayFailed && (
        <div className={styles.relayFailed}>
          <PlugOff aria-hidden />
          {t("explorer.encrypted.relay_failed", "Collaboration unavailable")}
        </div>
      )}
    </div>
  );
};
