/**
 * Mock server callbacks for OnlyOffice's connectMockServer() API.
 *
 * These callbacks replace OnlyOffice's Document Server entirely.
 * OnlyOffice calls these functions instead of making WOPI/REST requests.
 */

import type { MockServerCallbacks, OOChange, OOMessage } from "./types";
import { getParticipants, getLocalUser, getUniqueOOId } from "./participants";
import { handleOutgoingChanges, processOOEvent } from "./changesPipeline";

export interface MockServerOptions {
  /** Called when local user makes changes that should be broadcast */
  onLocalChanges: (changes: OOChange[]) => void;
  /** Called when a lock is requested (spreadsheets) */
  onLockRequest?: (locks: unknown) => void;
  /** Called when cursor position changes */
  onCursorUpdate?: (cursor: unknown) => void;
  /** Called when checkpoint should be triggered */
  onCheckpointNeeded?: () => void;
  /** Resolve an image name to a blob URL (for embedded images) */
  resolveImageURL?: (name: string) => Promise<string>;
}

/** Queue of changes from remote users to be applied on init */
let initialChangesQueue: OOChange[] = [];

/** The handler that OnlyOffice provides for receiving messages */
let ooMessageHandler: ((msg: OOMessage) => void) | null = null;

/**
 * Set the initial changes queue (populated from network history before editor loads).
 */
export function setInitialChanges(changes: OOChange[]): void {
  initialChangesQueue = changes;
}

/**
 * Send a message TO OnlyOffice (e.g. remote user's changes).
 *
 * This is the reverse direction: network → OnlyOffice.
 */
export function sendToEditor(msg: OOMessage): void {
  if (ooMessageHandler) {
    ooMessageHandler(msg);
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
  options: MockServerOptions,
): MockServerCallbacks {
  return {
    /**
     * OnlyOffice calls this to register its message handler.
     * The handler accepts messages FROM the collaboration layer.
     * OnlyOffice also calls this when it has outgoing messages (changes, locks, etc.).
     *
     * Note: In CryptPad, this dual purpose is handled in fromOOHandler().
     * OnlyOffice uses this both to:
     * 1. Register a handler for incoming messages (from other users)
     * 2. Send outgoing messages (local changes, lock requests)
     */
    onMessage(handler: (msg: OOMessage) => void) {
      // Store the handler so we can send remote changes to the editor
      ooMessageHandler = handler;

      // Return the function OnlyOffice should call with outgoing messages
      // This is the "fromOOHandler" in CryptPad terminology
      return (msg: OOMessage) => {
        const localUser = getLocalUser();
        const uniqueOOId = getUniqueOOId();
        const event = processOOEvent(msg);

        switch (event.action) {
          case "broadcast_changes": {
            const changes = handleOutgoingChanges(
              msg,
              uniqueOOId,
              localUser.ooId,
            );
            if (changes) {
              options.onLocalChanges(changes);
            }
            break;
          }
          case "lock_request":
            options.onLockRequest?.(event.data);
            break;
          case "cursor_update":
            options.onCursorUpdate?.(event.data);
            break;
          case "save_lock_check":
            // Respond that save lock is not held (Phase 1: single user)
            sendToEditor({
              type: "unSaveLock",
              isSaveLock: false,
            } as OOMessage);
            break;
        }
      };
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
      return "";
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
