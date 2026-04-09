/**
 * Participant management for OnlyOffice collaboration sessions.
 *
 * Tracks connected users and provides the participant list that
 * OnlyOffice expects via connectMockServer().getParticipants().
 */

import type { OOParticipant, OOParticipantList } from './types';

/** Colors assigned to participants for cursors and selections */
const PARTICIPANT_COLORS = [
  '#4285f4',
  '#ea4335',
  '#fbbc04',
  '#34a853',
  '#ff6d01',
  '#46bdc6',
  '#7baaf7',
  '#f07b72',
  '#fcd04f',
  '#71c287',
  '#ff9e40',
  '#78d9e0',
  '#a0c3ff',
  '#f4a8a0',
  '#fde293',
  '#a8dbb5',
];

export interface LocalUser {
  id: string; // Drive user ID (sub)
  name: string; // Display name
  ooId: number; // OnlyOffice user ID (random)
  index: number; // Unique index in participant list
  color: string; // Participant color
}

interface RemoteUser {
  id: string;
  name: string;
  ooId: number;
  index: number;
  connectionId: string;
  color: string;
}

let localUser: LocalUser | null = null;
const remoteUsers = new Map<string, RemoteUser>();
let nextIndex = 1;

/**
 * Initialize the local user.
 */
export function initLocalUser(userId: string, userName: string): LocalUser {
  const idx = nextIndex++;
  localUser = {
    id: userId,
    name: userName,
    ooId: Math.floor(Math.random() * 1000000),
    index: idx,
    color: PARTICIPANT_COLORS[(idx - 1) % PARTICIPANT_COLORS.length],
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
 * Get the unique OO ID for the local user (combined ooId + index).
 */
export function getUniqueOOId(): string {
  const user = getLocalUser();
  return String(user.ooId) + String(user.index);
}

/**
 * Add a remote user to the session.
 */
export function addRemoteUser(
  userId: string,
  userName: string,
  connectionId: string
): void {
  if (remoteUsers.has(userId)) return;
  const idx = nextIndex++;
  remoteUsers.set(userId, {
    id: userId,
    name: userName,
    ooId: Math.floor(Math.random() * 1000000),
    index: idx,
    connectionId,
    color: PARTICIPANT_COLORS[(idx - 1) % PARTICIPANT_COLORS.length],
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
 *
 * Includes all connected users plus a synthetic "History" participant
 * (CryptPad convention to signal collaborative editing mode).
 */
export function getParticipants(): OOParticipantList {
  const user = getLocalUser();

  const list: OOParticipant[] = [
    // Local user
    {
      id: String(user.ooId) + String(user.index),
      idOriginal: String(user.ooId),
      username: user.name,
      indexUser: user.index,
      connectionId: user.id,
      isCloseCoAuthoring: false,
      view: false,
    },
  ];

  // Remote users
  for (const remote of remoteUsers.values()) {
    list.push({
      id: String(remote.ooId) + String(remote.index),
      idOriginal: String(remote.ooId),
      username: remote.name,
      indexUser: remote.index,
      connectionId: remote.connectionId,
      isCloseCoAuthoring: false,
      view: false,
    });
  }

  // Synthetic "History" participant (signals collaborative mode to OnlyOffice)
  list.push({
    id: '0',
    idOriginal: '0',
    username: 'History',
    indexUser: 0,
    connectionId: '0',
    isCloseCoAuthoring: false,
    view: false,
  });

  return {
    index: user.index,
    list,
  };
}

/**
 * Reset all participant state (used on disconnect/reconnect).
 */
export function resetParticipants(): void {
  localUser = null;
  remoteUsers.clear();
  nextIndex = 1;
}
