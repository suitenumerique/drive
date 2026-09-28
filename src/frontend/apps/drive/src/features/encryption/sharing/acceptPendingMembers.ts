import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { getDriver } from "@/features/config/Config";
import { Access } from "@/features/drivers/types";
import { fetchRegisteredKeys } from "@/features/encryption/fetchRegisteredKeys";
import { useOnSuccessAccessOrInvitationMutation } from "@/features/explorer/hooks/useRefreshItems";

import { fetchSubtreeEntryKey } from "./wrapKeyForUser";

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Give pending members of the encrypted subtree `itemId` belongs to its key:
 * those who have enabled encryption since they were added get it wrapped for
 * their current key, in one vault call (so one verification prompt for every
 * recipient not yet trusted), and the others stay pending. Throws when the
 * vault refuses the wrap, e.g. when the caller declines to verify a
 * recipient: nobody is accepted then.
 */
export async function acceptPendingMembers(
  itemId: string,
  pending: Access[],
): Promise<{ accepted: Access[]; notReady: Access[] }> {
  const vaultClient = window.__driveVaultClient;
  if (!vaultClient) {
    throw new Error("Vault client not available");
  }
  const subs = pending.map((access) => access.user.sub).filter(Boolean);
  const { publicKeys, versions } = await fetchRegisteredKeys(subs);
  const ready = pending.filter((access) => !!publicKeys[access.user.sub]);
  const notReady = pending.filter((access) => !ready.includes(access));

  if (ready.length === 0) {
    return { accepted: [], notReady };
  }

  const entryKey = await fetchSubtreeEntryKey(itemId);
  const { encryptedKeys } = await vaultClient.shareKeys(
    entryKey,
    Object.fromEntries(
      ready.map((access) => [
        access.user.sub,
        { email: access.user.email, name: access.user.full_name },
      ]),
    ),
  );

  const driver = getDriver();
  const accepted: Access[] = [];
  for (const access of ready) {
    const wrappedKey = encryptedKeys[access.user.sub];
    if (!wrappedKey) {
      continue;
    }
    // The access row lives on the item where the share was granted (the
    // encryption root or an ancestor of the viewed item), not necessarily
    // on `itemId`: the PATCH must target that item.
    await driver.acceptEncryptionAccess(access.item.id, access.id, {
      encrypted_item_symmetric_key_for_user: arrayBufferToBase64(wrappedKey),
      encryption_public_key_version: versions[access.user.sub],
    });
    accepted.push(access);
  }

  return { accepted, notReady };
}

export function useAcceptPendingMembers() {
  const queryClient = useQueryClient();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();

  return useCallback(
    async (itemId: string, pending: Access[]) => {
      try {
        return await acceptPendingMembers(itemId, pending);
      } finally {
        for (const ownerId of new Set(pending.map((a) => a.item.id))) {
          onSuccessAccessOrInvitation(ownerId, false);
        }
        queryClient.invalidateQueries({ queryKey: ["itemAccesses", itemId] });
      }
    },
    [queryClient, onSuccessAccessOrInvitation],
  );
}
