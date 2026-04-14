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

// Index must be the SAME across clients for the same user, otherwise OO's
// participants map keys don't match the user field on incoming changes/cursors
// and attribution breaks. We use a fixed value of 1 for every participant —
// uniqueness is provided by the `sub` half of the id, not by the index.
const SHARED_INDEX = 1;

let localUser: LocalUser | null = null;
const remoteUsers = new Map<string, RemoteUser>();

/**
 * Initialize the local user.
 * Uses user.sub (OIDC UUID) as the OO ID — globally unique, no collision risk.
 */
export function initLocalUser(userId: string, userName: string): LocalUser {
  localUser = {
    driveId: userId,
    name: userName,
    index: SHARED_INDEX,
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
  remoteUsers.set(userId, {
    driveId: userId,
    name: userName,
    index: SHARED_INDEX,
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

  // OO computes change.user as `<config.user.id><indexUser>` and looks the
  // resulting string up in `_participants[id]`. So the participant `id` must
  // be the full internal form `<ooId><index>`, not just `<ooId>`.
  const localFullId = user.ooId + String(user.index);

  const list: OOParticipant[] = [
    {
      id: localFullId,
      idOriginal: localFullId,
      username: user.name,
      indexUser: user.index,
      connectionId: localFullId,
      isCloseCoAuthoring: false,
      view: false,
    },
  ];

  for (const remote of remoteUsers.values()) {
    const remoteFullId = remote.ooId + String(remote.index);
    list.push({
      id: remoteFullId,
      idOriginal: remoteFullId,
      username: remote.name,
      indexUser: remote.index,
      connectionId: remoteFullId,
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
 * Resolve a Drive user id (sub) to the OO internal id OO uses to attribute
 * cursors and changes (`<sub>_<indexUser>`). Returns null if the user is
 * not a known remote participant.
 */
export function getRemoteOOInternalId(driveUserId: string): string | null {
  const remote = remoteUsers.get(driveUserId);
  if (!remote) return null;
  return remote.ooId + String(remote.index);
}

/**
 * Build the message OnlyOffice expects to refresh its participants list
 * mid-session. OO calls getParticipants() once at init, so we have to push
 * fresh state via this `connectState` message whenever a peer joins/leaves.
 */
export function buildConnectStateMessage(): {
  type: 'connectState';
  participantsTimestamp: number;
  participants: OOParticipant[];
  waitAuth: boolean;
} {
  return {
    type: 'connectState',
    participantsTimestamp: Date.now(),
    participants: getParticipants().list,
    waitAuth: false,
  };
}

/**
 * Reset all participant state (used on disconnect/reconnect).
 */
export function resetParticipants(): void {
  localUser = null;
  remoteUsers.clear();
}
