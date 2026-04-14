/**
 * Participant management for OnlyOffice collaboration sessions.
 *
 * One identifier per user end-to-end: the Drive `sub`. We pass it as
 * `editorConfig.user.id` and as the participant `id`, and we push
 * `indexUser: ''` in the auth handshake so OO computes
 * `_userId = config.user.id + indexUser = sub`. That single id is then used
 * for changes, cursors, locks AND comment author attribution — without it
 * the comment-author embedded in change records (which uses the bare
 * `config.user.id`) would never match the participant entry (which used to
 * have an index suffix appended), and the receiver would silently drop
 * comments.
 */

import type { OOParticipant, OOParticipantList } from './types';

export interface LocalUser {
  driveId: string;
  name: string;
}

interface RemoteUser {
  driveId: string;
  name: string;
}

let localUser: LocalUser | null = null;
const remoteUsers = new Map<string, RemoteUser>();

export function initLocalUser(userId: string, userName: string): LocalUser {
  localUser = { driveId: userId, name: userName };
  return localUser;
}

export function getLocalUser(): LocalUser {
  if (!localUser) {
    throw new Error('Local user not initialized. Call initLocalUser() first.');
  }
  return localUser;
}

export function getUniqueOOId(): string {
  return getLocalUser().driveId;
}

export function getOOInternalUserId(): string {
  return getLocalUser().driveId;
}

export function addRemoteUser(
  userId: string,
  userName: string,
  _connectionId: string,
): void {
  if (localUser && userId === localUser.driveId) return;
  if (remoteUsers.has(userId)) return;
  remoteUsers.set(userId, { driveId: userId, name: userName });
}

export function removeRemoteUser(userId: string): void {
  remoteUsers.delete(userId);
}

export function getParticipants(): OOParticipantList {
  const user = getLocalUser();

  const list: OOParticipant[] = [
    {
      id: user.driveId,
      idOriginal: user.driveId,
      username: user.name,
      indexUser: '',
      connectionId: user.driveId,
      isCloseCoAuthoring: false,
      view: false,
    },
  ];

  for (const remote of remoteUsers.values()) {
    list.push({
      id: remote.driveId,
      idOriginal: remote.driveId,
      username: remote.name,
      indexUser: '',
      connectionId: remote.driveId,
      isCloseCoAuthoring: false,
      view: false,
    });
  }

  // History pseudo-participant forces collaborative mode in OO.
  list.push({
    id: '0',
    idOriginal: '0',
    username: 'History',
    indexUser: '',
    connectionId: '0',
    isCloseCoAuthoring: false,
    view: false,
  });

  return { index: '', list };
}

export function getRemoteOOInternalId(driveUserId: string): string | null {
  const remote = remoteUsers.get(driveUserId);
  return remote ? remote.driveId : null;
}

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

export function resetParticipants(): void {
  localUser = null;
  remoteUsers.clear();
}
