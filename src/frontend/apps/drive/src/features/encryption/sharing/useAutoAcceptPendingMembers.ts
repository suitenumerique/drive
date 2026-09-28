import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { useVaultClient } from "@/features/encryption/VaultClientProvider";

import { useAcceptPendingMembers } from "./acceptPendingMembers";

// Pending sets already tried in this tab, per item: a declined verification
// prompt must not come back each time the item is reopened. The share dialog
// keeps a manual Accept per member.
const attempted = new Set<string>();

/**
 * When someone who can manage members opens an encrypted item (a folder in
 * the explorer or a file in the preview), give its key to every pending member
 * who has enabled encryption since they were added. Without this a pending
 * member waits for someone to open the share dialog and click Accept.
 */
export const useAutoAcceptPendingMembers = (item: Item | undefined) => {
  const { client: vaultClient, hasKeys } = useVaultClient();
  const acceptPendingMembers = useAcceptPendingMembers();
  // The caller must hold the subtree key: a pending viewer would get a 403 on
  // the key chain.
  const enabled =
    !!item?.is_encrypted &&
    !!item.abilities?.accesses_manage &&
    !item.is_pending_encryption_for_user &&
    hasKeys === true &&
    !!vaultClient;
  const itemId = item?.id ?? "";
  const { data: accesses } = useQuery({
    queryKey: ["itemAccesses", itemId],
    queryFn: () => getDriver().getItemAccesses(itemId),
    enabled,
    staleTime: 0,
    gcTime: 0,
  });

  useEffect(() => {
    if (!enabled || !accesses) {
      return;
    }
    const pending = accesses.filter((access) => access.is_pending_encryption);
    const key = `${itemId}:${pending
      .map((access) => access.id)
      .sort()
      .join(",")}`;
    if (pending.length === 0 || attempted.has(key)) {
      return;
    }
    attempted.add(key);
    acceptPendingMembers(itemId, pending).catch((err: unknown) => {
      console.warn("Could not give pending members the item key:", err);
    });
  }, [enabled, itemId, accesses, acceptPendingMembers]);
};
