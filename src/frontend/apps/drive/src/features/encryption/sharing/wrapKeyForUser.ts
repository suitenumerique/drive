/**
 * Re-wrap an encrypted subtree's symmetric key for a specific user's
 * public key. Shared between two entry points:
 *
 *   1. First-time share — invitee is not yet on the access list; caller
 *      posts a new access along with the wrapped key.
 *   2. "Accept" — invitee is already on the access list as pending
 *      (they hold no wrapped key because they had no public key when
 *      they were added); caller sends the wrapped key once the invitee
 *      has completed their onboarding.
 *
 * Both paths need the same primitives: fetch the item's key chain, let
 * the vault resolve the item's own key from the caller's entry key down
 * the chain and wrap it for the invitee, and record the version of the
 * invitee's public key so the backend can track key-change events later.
 * Wrapping the entry key instead would store an ancestor's key on the
 * item: useless to open it, and the key of more than was shared.
 */

import { getDriver } from "@/features/config/Config";
import { fetchRegisteredKeys } from "@/features/encryption/fetchRegisteredKeys";

export interface WrappedKeyForUser {
  wrappedKeyBase64: string;
  version: number;
}

/**
 * A share recipient: the OIDC sub plus a display-only label (email required,
 * name optional). The vault wraps for the sub after its own binding + TOFU
 * trust check; the label is surfaced only if the "verify recipients" trust
 * modal opens, so callers pass the user's real email/name.
 */
export interface ShareRecipient {
  sub: string;
  email: string;
  name?: string;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
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
 * The key of an item on the caller's key chain to `itemId`, in the form the
 * vault resolves: the caller's entry wrap plus the wrapped keys from below
 * the entry point down to that item.
 */
export interface ChainKey {
  itemId: string;
  entryKey: ArrayBuffer;
  encryptedKeyChain?: ArrayBuffer[];
}

/**
 * Resolve, from the key chain of `itemId`, the key of `targetItemId`: an
 * ancestor-or-self of `itemId`. A target at or above the caller's entry
 * point resolves to the entry point itself, the highest key the caller holds.
 */
export async function fetchChainKey(
  itemId: string,
  targetItemIds: string[] = [itemId],
): Promise<Map<string, ChainKey>> {
  const keyChain = await getDriver().getKeyChain(itemId);
  const entryKey = base64ToArrayBuffer(keyChain.encrypted_key_for_user);
  const entryPoint: ChainKey = {
    itemId: keyChain.user_access_item_id,
    entryKey,
  };
  const keys = new Map<string, ChainKey>();
  for (const targetItemId of new Set(targetItemIds)) {
    const index = keyChain.chain.findIndex((e) => e.item_id === targetItemId);
    keys.set(
      targetItemId,
      index === -1
        ? entryPoint
        : {
            itemId: targetItemId,
            entryKey,
            encryptedKeyChain: keyChain.chain
              .slice(0, index + 1)
              .map((e) => base64ToArrayBuffer(e.encrypted_symmetric_key)),
          },
    );
  }
  return keys;
}

/**
 * Wrap the key of `key.itemId` for a single user. Returns null when the
 * user has no public key yet — the caller should create the access
 * without a key in that case, the user is then pending (or create
 * nothing, if this is a pre-check).
 */
export async function wrapSubtreeKeyForUser(
  key: ChainKey,
  recipient: ShareRecipient,
): Promise<WrappedKeyForUser | null> {
  const vaultClient = window.__driveVaultClient;
  if (!vaultClient) {
    throw new Error("Vault client not available");
  }
  const { sub, email, name } = recipient;
  const { publicKeys, versions } = await fetchRegisteredKeys([sub]);
  const userPublicKey = publicKeys[sub];
  if (!userPublicKey) {
    return null;
  }
  // Pass a labeled recipient map (sub → {email, name}): the vault resolves +
  // trust-checks the key itself (binding + TOFU). The fetched publicKey above
  // only gates on the user being registered; the label is display-only, shown
  // if the trust modal opens.
  const { encryptedKeys } = await vaultClient.shareKeys(
    key.entryKey,
    { [sub]: { email, name } },
    key.encryptedKeyChain,
  );
  const wrappedKey = encryptedKeys[sub];
  if (!wrappedKey) {
    return null;
  }
  return {
    wrappedKeyBase64: arrayBufferToBase64(wrappedKey),
    version: versions[sub],
  };
}
