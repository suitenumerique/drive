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
  resolveImageURL?: (name: string) => Promise<string>;
}

let initialChangesQueue: OOChange[] = [];
let editorInstance: any = null;

export function setEditorInstance(editor: any): void {
  editorInstance = editor;
}

export function setInitialChanges(changes: OOChange[]): void {
  initialChangesQueue = changes;
}

export function sendToEditor(msg: OOMessage): void {
  if (editorInstance) {
    editorInstance.sendMessageToOO(msg);
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
          options.onLockRequest?.('acquire', msg.block);
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
          if (msg.releaseLocks) {
            sendToEditor({
              type: 'releaseLock',
              locks: [msg.releaseLocks],
            } as OOMessage);
          }
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

        case 'forceSaveStart':
          sendToEditor({
            type: 'forceSave',
            success: true,
          } as OOMessage);
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
      const changes = [...initialChangesQueue];
      initialChangesQueue = [];
      return changes;
    },
  };
}
