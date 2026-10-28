/**
 * Entry point of the OnlyOffice sandbox page (built to
 * `public/onlyoffice-sandbox/host.js` by `scripts/build-onlyoffice-sandbox.mjs`).
 *
 * It takes a single MessagePort from its parent window, loads OnlyOffice
 * from this origin, and runs one editor session on the document Drive
 * sends. Everything else goes through the port: see `protocol.ts`.
 */

import { loadOnlyOffice, startEngine, type EngineHandle } from "./engine";
import {
  ONLYOFFICE_SANDBOX_PROTOCOL,
  SANDBOX_CONNECT,
  type HostToSandbox,
  type SandboxRpcMethod,
  type SandboxToHost,
} from "./protocol";

let port: MessagePort | null = null;
let engine: EngineHandle | null = null;
let nextRpcId = 1;
const pendingRpcs = new Map<
  number,
  { resolve: (value: unknown) => void; reject: (error: Error) => void }
>();

const post = (message: SandboxToHost, transfer: Transferable[] = []) => {
  port?.postMessage(message, transfer);
};

const call = (
  method: SandboxRpcMethod,
  args: unknown[],
  transfer: Transferable[] = [],
): Promise<unknown> => {
  const id = nextRpcId++;
  return new Promise((resolve, reject) => {
    pendingRpcs.set(id, { resolve, reject });
    post({ type: "rpc", id, method, args }, transfer);
  });
};

const handle = (message: HostToSandbox) => {
  switch (message.type) {
    case "init":
      if (engine || message.init.protocol !== ONLYOFFICE_SANDBOX_PROTOCOL)
        return;
      engine = startEngine(message.init, {
        emit: (event) =>
          post(event, event.type === "export" ? [event.bytes] : []),
        call,
      });
      return;
    case "relay:event":
      engine?.onRelayEvent(message.name, message.args, message.joinedAt);
      return;
    case "rpc:result": {
      const pending = pendingRpcs.get(message.id);
      if (!pending) return;
      pendingRpcs.delete(message.id);
      if (message.ok) pending.resolve(message.value);
      else pending.reject(new Error(message.error));
      return;
    }
    case "command":
      if (!engine) {
        post({ type: "command:result", id: message.id, ok: false });
        return;
      }
      engine
        .command(message.name)
        .then(() => post({ type: "command:result", id: message.id, ok: true }))
        .catch((error) =>
          post({
            type: "command:result",
            id: message.id,
            ok: false,
            error: String(error).slice(0, 2000),
          }),
        );
      return;
  }
};

// The port arrives once, from Drive's page, which frames us through an empty
// page of its own. A frame of any other page gets nothing from Drive, so
// accepting only the top window is enough: this page holds no secret.
window.addEventListener("message", (event) => {
  if (port || event.source !== window.top) return;
  const data = event.data as { type?: unknown; protocol?: unknown } | null;
  if (
    data?.type !== SANDBOX_CONNECT ||
    data.protocol !== ONLYOFFICE_SANDBOX_PROTOCOL ||
    !event.ports[0]
  )
    return;
  port = event.ports[0];
  port.onmessage = (e: MessageEvent<HostToSandbox>) => handle(e.data);
  loadOnlyOffice()
    .then(() => post({ type: "ready" }))
    .catch((error) =>
      post({ type: "failure", code: null, message: String(error) }),
    );
});

window.addEventListener("pagehide", () => engine?.destroy());
