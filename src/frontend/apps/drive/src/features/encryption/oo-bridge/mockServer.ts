import type { MockServerCallbacks, OOChange, OOMessage } from './types';
import {
  getParticipants,
  getOOInternalUserId,
  getRemoteOOInternalId,
} from './participants';
import { wrapOutgoingSaveChanges, getPatchIndex } from './changesPipeline';
import type { LockArbitrator } from './lockArbitrator';

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
  /**
   * Replicated lock arbitrator. When provided, `getLock` stops auto-
   * granting and instead consults the arbitrator (which broadcasts the
   * request through the relay, waits for settlement, and applies
   * first-stamp-wins). Used for Word (paragraph-id keys), Calc and
   * Presentation (`block.guid` keys). Our own userId is passed
   * alongside so the arbitrator can attribute claims.
   */
  lockArbitrator?: LockArbitrator;
  /** Current user's stable id (matches what the relay broadcasts). */
  userId?: string;
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

/**
 * Paragraph keys for which we've sent a `getLock` reply to the local OO
 * attributing ownership to a REMOTE peer. Tracking them lets us push a
 * matching `releaseLock` later (on peer release, leave, crash) without
 * referencing paragraphs OO doesn't know about — which was the source
 * of the `_onGetLock` / `_onReleaseLock` crashes (undefined paragraph
 * lookups hitting `Set_UserId` / `Set_Type`).
 *
 * CryptPad echoes a full arbitrator snapshot on any replicated-state
 * change. That works for them because ChainPad gives them a synchronous
 * CRDT update where doc changes and lock changes apply atomically. In
 * our relay model, a peer's `oo:lockRequest` can arrive before its
 * `saveChanges` has been applied to OO's document model, so a snapshot
 * push can reference a paragraph that doesn't exist yet on this side.
 * We therefore only expose a lock to OO when OO has just `askLock`ed
 * for it — at that moment the paragraph is guaranteed to exist in OO's
 * doc model, otherwise OO couldn't be asking.
 */
const peerLocksShownToEditor = new Set<string>();

/**
 * Remove `keys` from the tracking set and return the subset that was
 * actually tracked. Callers use the return value as a filter before
 * pushing `releaseLock` to OO: if we never told OO about a key, OO has
 * no marker to clear and pushing the release would be a no-op at best
 * and a crash at worst (on paragraphs OO doesn't know about).
 */
export function consumePeerLocksShownToEditor(keys: string[]): string[] {
  const known: string[] = [];
  for (const key of keys) {
    if (peerLocksShownToEditor.delete(key)) known.push(key);
  }
  return known;
}

/** Reset the tracking set. Call on relay reconnect / editor recreation. */
export function resetPeerLocksShownToEditor(): void {
  peerLocksShownToEditor.clear();
}

/**
 * Record that we've just told OO about `key` belonging to a remote
 * peer. Used by the eager push path for cell / slide remote claims —
 * `getLock` is sent to OO BEFORE OO ever asks, so the tracking set
 * needs to be populated from the caller side.
 */
export function addPeerLockShownToEditor(key: string): void {
  peerLocksShownToEditor.add(key);
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
          // OO sends `block` as an array of block descriptors. For
          // Excel/Presentation/PDF each descriptor is an object with a
          // `guid` property; for Word it's a plain string.
          //
          // `_onGetLock` in the SDK (DocsCoApi) iterates `data.locks`
          // with `for (key in ...)` — so `locks` must be a plain object,
          // NOT an array. For Excel/Presentation/PDF it reads
          // `lock.block.guid`; for Word it uses the object key directly.
          const blockArray = (msg.block as unknown[]) || [];

          // All docTypes go through the replicated arbitrator. Per-type
          // key extraction:
          //   - word  → `JSON.stringify(block)` (block is a paragraph id
          //             string; JSON.stringify keeps the existing key
          //             format, important for compatibility with the
          //             Word peer-tracking already in the wild)
          //   - cell  → `block.guid` (workbook-stable GUID assigned by
          //             OO for the cell range being edited)
          //   - slide → `block.guid` (slide / shape GUID)
          //
          // Without an arbitrator (legacy / test setup) we fall through
          // to the optimistic auto-grant below — that path stays for
          // single-user mode where there's no relay to coordinate with.
          const keyForBlock = (block: unknown): string | null => {
            if (options.docType === 'word') {
              return typeof block === 'string'
                ? block
                : JSON.stringify(block);
            }
            // cell / slide
            const guid = (block as { guid?: unknown } | null)?.guid;
            return typeof guid === 'string' ? guid : null;
          };

          if (options.lockArbitrator && options.userId) {
            const arbitrator = options.lockArbitrator;
            const userId = options.userId;
            // Pair each requested block with its arbitration key so the
            // reply can echo the original block (cell/slide need the
            // `block.guid` field intact for OO's `_onGetLock`).
            const requested: Array<{ key: string; block: unknown }> = [];
            for (const block of blockArray) {
              const key = keyForBlock(block);
              if (key) requested.push({ key, block });
            }
            const keys = requested.map(r => r.key);
            // Word's key IS the block (paragraph id string), no need
            // to ship it twice. Cell / Slide need the full descriptor
            // so peers can hand it to OO verbatim — `_onUpdateCFLock`
            // and friends read `block.sheetId` / `block.rangeType`,
            // not just `block.guid`.
            const blocks =
              options.docType === 'word'
                ? undefined
                : requested.map(r => r.block);
            void arbitrator
              .tryClaim(userId, keys, blocks)
              .then(() => {
                // Reply with ownership for ONLY the keys OO asked about —
                // never the full snapshot. The snapshot approach crashed
                // OO (`Set_UserId on undefined` inside `_onGetLock`) when
                // it referenced resources a peer had just created but
                // whose `saveChanges` hadn't reached this side's doc
                // model yet. Keys OO is currently asking about are
                // guaranteed to exist in its model — otherwise OO
                // couldn't be asking — so this restriction eliminates
                // the "unknown resource" class of crash entirely.
                //
                // Also track peer-owned keys so `releaseLock` pushes on
                // later peer release stay scoped to resources OO knows.
                const locks: Record<string, unknown> = {};
                const byKey = new Map(
                  arbitrator.snapshot().map(e => [e.key, e]),
                );
                for (const { key, block } of requested) {
                  const entry = byKey.get(key);
                  if (!entry) continue;
                  if (entry.userId === userId) {
                    locks[key] = {
                      time: entry.timestampMs,
                      user: ooInternalId,
                      block,
                    };
                  } else {
                    const peerOOId =
                      getRemoteOOInternalId(entry.userId) ?? entry.userId;
                    locks[key] = {
                      time: entry.timestampMs,
                      user: peerOOId,
                      block,
                    };
                    peerLocksShownToEditor.add(key);
                  }
                }
                sendToEditor({ type: 'getLock', locks } as any);
              })
              .catch(err => {
                // Arbitration failed (usually the socket closed mid-
                // request). Fall back to "deny everything" — OO will
                // retry after its internal delay and by then we'll
                // either have a fresh connection or have surfaced the
                // disconnect to the user.
                console.warn('[lockArbitrator] claim failed:', err);
                sendToEditor({ type: 'getLock', locks: {} } as any);
              });
            break;
          }

          // No arbitrator wired (single-user / test). Auto-grant
          // everything.
          const locks: Record<string, unknown> = {};
          for (const block of blockArray) {
            const key = keyForBlock(block);
            if (!key) continue;
            locks[key] = {
              time: Date.now(),
              user: ooInternalId,
              block,
            };
          }
          sendToEditor({ type: 'getLock', locks } as any);
          break;
        }

        case 'saveChanges': {
          const wrapped = wrapOutgoingSaveChanges(msg, ooInternalId);
          if (wrapped) {
            options.onSaveChangesBroadcast(wrapped);
          }

          // Cell / slide: release every lock we hold once the changes
          // have been broadcast. OO calls `unLockDocument` only on
          // blur / explicit save — without this release-on-commit
          // path, a user navigating cell to cell leaves a trail of
          // locks visible to peers ("red dotted border that never
          // clears"). CryptPad does the same release-on-handleChanges
          // for every doc type. We only do it for cell / slide
          // because Word has a structural-edit race: freeing a
          // paragraph before OO has applied our own outgoing
          // saveChanges lets a peer claim + structurally mutate the
          // "old" shape, which crashes later in
          // `private_UpdateMarksOnSplit`. Word releases stay tied to
          // explicit `unLockDocument`.
          if (
            (options.docType === 'cell' || options.docType === 'slide') &&
            options.lockArbitrator &&
            options.userId &&
            msg.endSaveChanges !== false
          ) {
            void options.lockArbitrator
              .releaseAll(options.userId)
              .catch(err => {
                console.warn(
                  '[lockArbitrator] release-on-saveChanges failed:',
                  err,
                );
              });
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
          // Tell peers we're dropping every lock we hold. OO doesn't
          // enumerate them here — it just asks the server to release
          // "all mine" — so we delegate to the arbitrator's releaseAll
          // which scans the replicated table for our entries and
          // broadcasts a release for each. Applies to Word, Cell and
          // Slide alike now that all three use the same arbitrator;
          // before this generalisation Calc/Slide leaked locks forever
          // because their `lock:acquire` had no matching release.
          if (options.lockArbitrator && options.userId) {
            void options.lockArbitrator
              .releaseAll(options.userId)
              .catch(err => {
                console.warn('[lockArbitrator] releaseAll failed:', err);
              });
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
