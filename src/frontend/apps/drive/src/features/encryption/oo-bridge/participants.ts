/**
 * Participant management for OnlyOffice collaboration sessions.
 *
 * Tracks connected users and provides the participant list that
 * OnlyOffice expects via connectMockServer().getParticipants().
 *
 * IMPORTANT: OnlyOffice uses multiple ID fields (id, idOriginal, indexUser,
 * connectionId) and checks them in different places for lock ownership,
 * cursor display, etc. ALL must be consistent.
 */

import type { OOParticipant, OOParticipantList } from './types';

export interface LocalUser {
  driveId: string; // Drive user ID (sub)
  name: string; // Display name
  index: number; // Unique index in participant list (1-based)
  ooId: string; // The single consistent ID used everywhere in OO
}

interface RemoteUser {
  driveId: string;
  name: string;
  index: number;
  ooId: string;
}

let localUser: LocalUser | null = null;
const remoteUsers = new Map<string, RemoteUser>();
let nextIndex = 1;

/**
 * Initialize the local user.
 * Uses user.sub (OIDC UUID) as the OO ID — globally unique, no collision risk.
 */
export function initLocalUser(userId: string, userName: string): LocalUser {
  const idx = nextIndex++;
  localUser = {
    driveId: userId,
    name: userName,
    index: idx,
    // userId is user.sub (UUID like "d4e5f6a7-b8c9-..."), unique per user.
    // OO internally concatenates config.user.id + indexUser (no separator).
    // Trailing underscore so the boundary is visible in logs: "uuid_1" not "uuid1".
    ooId: userId + '_',
  };
  return localUser;
}

/**
 * Get the local user.
 */
export function getLocalUser(): LocalUser {
  if (!localUser) {
    throw new Error('Local user not initialized. Call initLocalUser() first.');
  }
  return localUser;
}

/**
 * Get the OO ID for the local user (used in editor config user.id).
 */
export function getUniqueOOId(): string {
  return getLocalUser().ooId;
}

/**
 * Get the OO-internal userId that sdkjs constructs.
 *
 * OnlyOffice sdkjs computes: _userId = config.user.id + auth.indexUser
 * This concatenated value is used for lock ownership and change attribution.
 * Lock entries and change entries MUST use this value, not getUniqueOOId().
 */
export function getOOInternalUserId(): string {
  const user = getLocalUser();
  // Matches: this._userId = this._user.asc_getId() + this._indexUser
  // where asc_getId() returns editorConfig.user.id (= user.ooId)
  // and _indexUser comes from auth response indexUser (= user.index)
  return user.ooId + String(user.index);
}

/**
 * Add a remote user to the session.
 */
export function addRemoteUser(
  userId: string,
  userName: string,
  _connectionId: string
): void {
  // Skip if it's the local user (e.g. stale relay connection from previous page load)
  if (localUser && userId === localUser.driveId) return;
  if (remoteUsers.has(userId)) return;
  const idx = nextIndex++;
  remoteUsers.set(userId, {
    driveId: userId,
    name: userName,
    index: idx,
    ooId: userId + '_',
  });
}

/**
 * Remove a remote user from the session.
 */
export function removeRemoteUser(userId: string): void {
  remoteUsers.delete(userId);
}

/**
 * Get the participant list in the format OnlyOffice expects.
 */
export function getParticipants(): OOParticipantList {
  const user = getLocalUser();

  const list: OOParticipant[] = [
    // Local user
    {
      id: user.ooId,
      idOriginal: user.ooId, // MUST match id — OO checks both
      username: user.name,
      indexUser: user.index,
      connectionId: user.ooId,
      isCloseCoAuthoring: false,
      view: false,
    },
  ];

  // Remote users
  for (const remote of remoteUsers.values()) {
    list.push({
      id: remote.ooId,
      idOriginal: remote.ooId,
      username: remote.name,
      indexUser: remote.index,
      connectionId: remote.ooId,
      isCloseCoAuthoring: false,
      view: false,
    });
  }

  // History participant forces collaborative mode (OO uses getLock/saveChanges)
  // Without it (single participant), OO uses a different non-collaborative save path
  list.push({
    id: '0',
    idOriginal: '0',
    username: 'History',
    indexUser: 0,
    connectionId: '0',
    isCloseCoAuthoring: false,
    view: false,
  });

  const result = {
    index: user.index,
    list,
  };
  return result;
}

/**
 * Reset all participant state (used on disconnect/reconnect).
 */
export function resetParticipants(): void {
  localUser = null;
  remoteUsers.clear();
  nextIndex = 1;
}
