/**
 * Re-wrap an encrypted subtree's symmetric key for a specific user's
 * public key. Shared between two entry points:
 *
 *   1. First-time share — invitee is not yet on the access list; caller
 *      posts a new access row along with the wrapped key.
 *   2. "Accept" — invitee is already on the access list as pending
 *      (their row has a NULL wrapped key because they had no public key
 *      when they were added); caller PATCHes the row with the new
 *      wrapped key once the invitee has completed their onboarding.
 *
 * Both paths need the same primitives: fetch the subtree's key chain,
 * unwrap the caller's own entry key, wrap it for the invitee, and
 * compute the fingerprint of the invitee's public key so the backend
 * can track key-change events later.
 */

import { getDriver } from '@/features/config/Config';

export interface WrappedKeyForUser {
  wrappedKeyBase64: string;
  fingerprint: string;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Fetch the caller's wrapped entry key for the subtree `itemId` belongs
 * to, as an ArrayBuffer ready to be fed into `vaultClient.shareKeys`.
 */
export async function fetchSubtreeEntryKey(
  itemId: string,
): Promise<ArrayBuffer> {
  const driver = getDriver();
  const keyChain = await driver.getKeyChain(itemId);
  return base64ToArrayBuffer(keyChain.encrypted_key_for_user);
}

/**
 * Wrap `encryptedSymmetricKey` for a single user. Returns null when the
 * user has no public key yet — the caller should create a pending
 * access row in that case (or no row at all, if this is a pre-check).
 */
export async function wrapSubtreeKeyForUser(
  encryptedSymmetricKey: ArrayBuffer,
  userSub: string,
): Promise<WrappedKeyForUser | null> {
  const vaultClient = window.__driveVaultClient;
  if (!vaultClient) {
    throw new Error('Vault client not available');
  }
  const { publicKeys } = await vaultClient.fetchPublicKeys([userSub]);
  const userPublicKey = publicKeys[userSub];
  if (!userPublicKey) {
    return null;
  }
  const { encryptedKeys } = await vaultClient.shareKeys(
    encryptedSymmetricKey,
    { [userSub]: userPublicKey },
  );
  const wrappedKey = encryptedKeys[userSub];
  if (!wrappedKey) {
    return null;
  }
  const fingerprint = await vaultClient.computeKeyFingerprint(userPublicKey);
  return {
    wrappedKeyBase64: arrayBufferToBase64(wrappedKey),
    fingerprint,
  };
}
