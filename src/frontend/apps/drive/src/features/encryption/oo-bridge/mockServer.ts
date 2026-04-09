/**
 * Mock server callbacks for OnlyOffice's connectMockServer() API.
 *
 * These callbacks replace OnlyOffice's Document Server entirely.
 * OnlyOffice calls these functions instead of making WOPI/REST requests.
 */

import type { MockServerCallbacks, OOChange, OOMessage } from './types';
import { getParticipants, getLocalUser, getUniqueOOId } from './participants';
import { handleOutgoingChanges, getPatchIndex } from './changesPipeline';

export interface MockServerOptions {
  /** Called when local user makes changes that should be broadcast */
  onLocalChanges: (changes: OOChange[]) => void;
  /** Called when a lock is requested (spreadsheets) */
  onLockRequest?: (type: 'acquire' | 'release', locks: unknown) => void;
  /** Called when cursor position changes */
  onCursorUpdate?: (cursor: unknown) => void;
  /** Called when save lock is checked */
  onSaveLockCheck?: () => boolean;
  /** Resolve an image name to a blob URL (for embedded images) */
  resolveImageURL?: (name: string) => Promise<string>;
}

/** Queue of changes from remote users to be applied on init */
let initialChangesQueue: OOChange[] = [];

/** Reference to the OnlyOffice editor instance for sending messages TO the editor */
let editorInstance: any = null;

/**
 * Set the editor instance (called after DocEditor is created).
 */
export function setEditorInstance(editor: any): void {
  editorInstance = editor;
}

/**
 * Set the initial changes queue (populated from network history before editor loads).
 */
export function setInitialChanges(changes: OOChange[]): void {
  initialChangesQueue = changes;
}

/**
 * Send a message TO OnlyOffice via the editor's sendMessageToOO method.
 */
export function sendToEditor(msg: OOMessage): void {
  if (editorInstance) {
    editorInstance.sendMessageToOO(msg);
  }
}

/**
 * Create the connectMockServer() callbacks.
 *
 * Returns the 5 callbacks that OnlyOffice expects:
 * - onMessage: receives a handler for sending messages TO OnlyOffice
 * - getParticipants: returns the current user list
 * - onAuth: called when the editor is ready
 * - getImageURL: resolves image names to blob URLs
 * - getInitialChanges: returns queued changes from history
 */
export function createMockServerCallbacks(
  options: MockServerOptions
): MockServerCallbacks {
  return {
    /**
     * Called by OnlyOffice for each message FROM the editor (changes, locks, etc.).
     * This is NOT a handler setter — it receives the actual message.
     */
    onMessage(msg: OOMessage) {
      console.log('[mockServer]', msg.type, msg);
      const localUser = getLocalUser();
      const uniqueOOId = getUniqueOOId();

      switch (msg.type) {
        case 'auth':
        case 'authChangesAck':
        case 'clientLog':
          // Handled by OnlyOffice API wrapper or informational — no response needed
          break;

        case 'isSaveLock':
          // OnlyOffice asks if someone else is saving — always say no
          sendToEditor({
            type: 'saveLock',
            saveLock: options.onSaveLockCheck?.() ?? false,
          } as OOMessage);
          break;

        case 'getLock': {
          // OnlyOffice requests a lock before editing — grant it immediately
          // Response format must match what OnlyOffice expects:
          // For docs: object { lockId: { time, user, block } }
          // For sheets: array [ { time, user, block } ]
          const lockBlock = msg.block?.[0];
          const lockEntry = {
            time: Date.now(),
            user: uniqueOOId,
            block: lockBlock,
          };

          // Try array format (works for all document types)
          sendToEditor({
            type: 'getLock',
            locks: [lockEntry],
          } as OOMessage);

          options.onLockRequest?.('acquire', msg.block);
          break;
        }

        case 'saveChanges': {
          // OnlyOffice sends edited content — broadcast to peers
          const changes = handleOutgoingChanges(msg, uniqueOOId, localUser.ooId);
          if (changes) {
            options.onLocalChanges(changes);
          }

          // Acknowledge so OnlyOffice unblocks editing
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
          // OnlyOffice releases locks after saving
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

        case 'getMessages':
          // OO chat — not implemented, send empty response
          sendToEditor({ type: 'message' } as OOMessage);
          break;

        case 'forceSaveStart':
          // Force save request — acknowledge
          sendToEditor({
            type: 'forceSave',
            success: true,
          } as OOMessage);
          break;

        default:
          // Unknown message type — log for debugging
          break;
      }
    },

    /**
     * Return the current participant list.
     */
    getParticipants,

    /**
     * Called when the editor is ready for collaboration.
     */
    onAuth() {
      // Editor is ready — nothing special needed for Phase 1
    },

    /**
     * Resolve an image name to a displayable URL.
     * For encrypted files, images are decrypted and served as blob URLs.
     */
    async getImageURL(name: string): Promise<string> {
      if (options.resolveImageURL) {
        return options.resolveImageURL(name);
      }
      // Fallback: return empty (image will show as broken)
      return '';
    },

    /**
     * Return queued changes from remote users.
     * These are applied when the editor first loads.
     */
    getInitialChanges(): OOChange[] {
      const changes = [...initialChangesQueue];
      initialChangesQueue = [];
      return changes;
    },
  };
}
