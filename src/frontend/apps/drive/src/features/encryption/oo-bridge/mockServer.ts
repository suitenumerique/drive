import type { MockServerCallbacks, OOChange, OOMessage } from './types';
import { getParticipants, getOOInternalUserId } from './participants';
import { wrapOutgoingSaveChanges, getPatchIndex } from './changesPipeline';

export interface MockServerOptions {
  docType: 'word' | 'cell' | 'slide';
  /** Forward an opaque OO `saveChanges` message to peers (full envelope). */
  onSaveChangesBroadcast: (message: Record<string, unknown>) => void;
  onLockRequest?: (type: 'acquire' | 'release', locks: unknown) => void;
  onCursorUpdate?: (cursor: unknown) => void;
  onSaveLockCheck?: () => boolean;
  onMessageBroadcast?: (messages: unknown[]) => void;
  onMetaBroadcast?: (messages: unknown[]) => void;
  /**
   * Called when OO triggers its own `forceSave` (e.g. user hits
   * Cmd+S, or OO's internal forceSave timer fires). We do NOT echo
   * any acknowledgement back to OO because real OO servers reply
   * with a payload shape `_onForceSave` reads `.type` on each
   * entry of, and our simplified reply makes it crash. Instead we
   * route to the host's own checkpointing `forceSave()`.
   */
  onForceSaveRequest?: () => void;
  resolveImageURL?: (name: string) => Promise<string>;
}

let editorInstance: any = null;
/**
 * Diagnostic counter — when > 0, every `sendToEditor` call is logged
 * with its type, payload summary, return value, and any exception.
 * Toggled on during the preload drain so we can see whether OO is
 * accepting or silently dropping replayed events.
 */
let verboseSends = 0;

export function setEditorInstance(editor: any): void {
  editorInstance = editor;
}

export function setVerboseSends(enabled: boolean): void {
  verboseSends = enabled ? verboseSends + 1 : Math.max(0, verboseSends - 1);
}

export function sendToEditor(msg: OOMessage): void {
  if (!editorInstance) {
    if (verboseSends > 0) {
      console.log('[sendToEditor] NO EDITOR — dropping', msg?.type);
    }
    return;
  }
  if (verboseSends === 0) {
    editorInstance.sendMessageToOO(msg);
    return;
  }
  // Verbose path — wrap with logging and exception capture.
  const type = (msg as { type?: string }).type;
  const summary: Record<string, unknown> = { type };
  const anyMsg = msg as Record<string, unknown>;
  if (Array.isArray(anyMsg.changes)) {
    summary.changesCount = (anyMsg.changes as unknown[]).length;
    summary.changesIndex = anyMsg.changesIndex;
    summary.syncChangesIndex = anyMsg.syncChangesIndex;
    summary.startSaveChanges = anyMsg.startSaveChanges;
    summary.endSaveChanges = anyMsg.endSaveChanges;
    summary.isCoAuthoring = anyMsg.isCoAuthoring;
  }
  if (anyMsg.messages) {
    summary.messagesCount = Array.isArray(anyMsg.messages)
      ? (anyMsg.messages as unknown[]).length
      : 1;
  }
  console.log('[sendToEditor → OO] in', summary);
  try {
    const result = editorInstance.sendMessageToOO(msg);
    console.log('[sendToEditor ← OO] out', { type, result });
  } catch (err) {
    console.error('[sendToEditor ← OO] THREW', { type, err });
  }
}

export function createMockServerCallbacks(
  options: MockServerOptions,
): MockServerCallbacks {
  return {
    onMessage(msg: OOMessage) {
      const ooInternalId = getOOInternalUserId();

      switch (msg.type) {
        case 'auth':
        case 'authChangesAck':
        case 'clientLog':
          break;

        case 'isSaveLock':
          sendToEditor({
            type: 'saveLock',
            saveLock: options.onSaveLockCheck?.() ?? false,
          } as OOMessage);
          break;

        case 'getLock': {
          const lockBlock = (msg.block as unknown[] | undefined)?.[0] as
            | string
            | undefined;
          const lockEntry = {
            time: Date.now(),
            user: ooInternalId,
            block: lockBlock,
          };

          let locks: unknown;
          if (options.docType === 'cell') {
            locks = [lockEntry];
          } else {
            // Word / Slide expect an object keyed by the block value itself
            locks = lockBlock ? { [lockBlock]: lockEntry } : {};
          }

          sendToEditor({ type: 'getLock', locks } as OOMessage);
          // Broadcast lock acquisition to other peers ONLY for
          // spreadsheets. Word / slide use the OT channel
          // (`saveChanges`) for conflict handling, and OO's
          // `_onGetLock` on slide expects a doc-type-specific
          // shape we can't faithfully reconstruct on the receiver —
          // forwarding raw `msg.block` crashes the peer's editor
          // with `undefined.guid`. We never surfaced peer-lock
          // state in the UI for word/slide anyway.
          if (options.docType === 'cell') {
            options.onLockRequest?.('acquire', msg.block);
          }
          break;
        }

        case 'saveChanges': {
          const wrapped = wrapOutgoingSaveChanges(msg, ooInternalId);
          if (wrapped) {
            options.onSaveChangesBroadcast(wrapped);
          }

          if (msg.endSaveChanges !== false) {
            sendToEditor({
              type: 'unSaveLock',
              index: getPatchIndex(),
              time: Date.now(),
            } as OOMessage);
          } else {
            sendToEditor({
              type: 'savePartChanges',
              changesIndex: -1,
              time: Date.now(),
            } as OOMessage);
          }
          break;
        }

        case 'unLockDocument': {
          // NOTE: we intentionally do NOT echo a `releaseLock` frame
          // back to the sender. The real OO collab server only
          // broadcasts `releaseLock` to OTHER peers — the sender has
          // already dropped its own locks from client state before
          // calling `unLockDocument`. Echoing to self makes
          // `DocsCoApi._onReleaseLock` iterate `locks` looking up
          // guids that no longer exist; on slide (presentation) the
          // lock shape is an array of arrays and an inner element is
          // `undefined`, which throws `Cannot read properties of
          // undefined (reading 'guid')` and poisons the editor. The
          // only useful reply here is `unSaveLock` when `isSave` is
          // set — inter-peer lock visibility is already covered by
          // the `lock:acquire`/`lock:release` channel.
          if (msg.isSave) {
            sendToEditor({
              type: 'unSaveLock',
              index: getPatchIndex(),
              time: Date.now(),
            } as OOMessage);
          }
          break;
        }

        case 'cursor':
          options.onCursorUpdate?.(msg.cursor);
          break;

        case 'message': {
          const payload = (msg as any).messages
            ? ((msg as any).messages as unknown[])
            : (msg as any).message !== undefined
              ? [(msg as any).message]
              : [];
          if (payload.length > 0) {
            options.onMessageBroadcast?.(payload);
          }
          break;
        }

        case 'meta': {
          const payload =
            ((msg as any).messages as unknown[] | undefined) ?? [];
          if (payload.length > 0) {
            options.onMetaBroadcast?.(payload);
          }
          break;
        }

        case 'getMessages':
          sendToEditor({ type: 'message' } as OOMessage);
          break;

        case 'forceSave':
        case 'forceSaveStart':
          // DO NOT echo anything to OO here. Real DocServer replies
          // with a payload `_onForceSave` iterates reading `.type`
          // on each element; any simplified reply crashes OO with
          // `Cannot read properties of undefined (reading 'type')`.
          // Route the user's intent to our own checkpointing layer
          // instead — that's where the real save lives.
          options.onForceSaveRequest?.();
          break;

        default:
          break;
      }
    },

    getParticipants,

    onAuth() {
      // editor ready
    },

    async getImageURL(name: string): Promise<string> {
      if (options.resolveImageURL) {
        return options.resolveImageURL(name);
      }
      return '';
    },

    getInitialChanges(): OOChange[] {
      // Always empty: we route every inbound saveChanges through
      // `sendMessageToOO` (live path), including history replay. OO's
      // `handleChanges` / `_openDocumentEndCallback` path is not used.
      return [];
    },
  };
}
