import { getDriver } from "@/features/config/Config";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRemoveItemsFromPaginatedList } from "../hooks/useOptimisticPagination";
import {
  getMyFilesQueryKey,
  getRecentItemsQueryKey,
  getSharedWithMeQueryKey,
} from "@/utils/defaultRoutes";
import { MoveRequiresEncryption } from "@/features/drivers/Driver";
import {
  EncryptionRequestCancelled,
  useRecursiveEncrypt,
} from "@/features/encryption/RecursiveEncryptProvider";

export const useMoveItems = () => {
  type MoveItemPayload = {
    ids: string[];
    parentId?: string;
    oldParentId?: string;
  };

  const queryClient = useQueryClient();
  const driver = getDriver();
  const { requestEncryption } = useRecursiveEncrypt();

  const removeItems = useRemoveItemsFromPaginatedList();

  /**
   * Move a single item, intercepting the one encryption-boundary case
   * the driver can't handle in-line: plaintext → encrypted folder. The
   * driver throws `MoveRequiresEncryption('plaintext-into-encrypted')`,
   * we open the recursive-encryption modal for the source first, then
   * retry the move on success.
   *
   * Other cross-boundary cases are now handled by the driver itself:
   *   - encrypted → encrypted (same root): in-line rewrap of the
   *     item's K under the new parent's chain.
   *   - encrypted → plaintext (or workspace root): in-line re-anchor
   *     as its own encryption root (per-user wraps via `shareKeys`),
   *     no modal involved, no decryption.
   *   - cross-root remains an error the caller surfaces verbatim.
   */
  const moveOne = async (id: string, parentId?: string): Promise<void> => {
    try {
      await driver.moveItem(id, parentId);
    } catch (e) {
      if (
        !(e instanceof MoveRequiresEncryption) ||
        e.reason !== 'plaintext-into-encrypted'
      ) {
        throw e;
      }
      const item = await driver.getItem(id);
      try {
        await requestEncryption(item);
      } catch (modalErr) {
        if (modalErr instanceof EncryptionRequestCancelled) {
          return; // User closed the modal — abort the move silently.
        }
        throw modalErr;
      }
      // After encryption the item is self-rooted; the retry routes
      // through case 4 (demote into chain) on the driver. If the retry
      // throws, surface it loudly — silent failures here let the
      // optimistic tree update (DnD already moved the node visually)
      // diverge from server reality.
      try {
        await driver.moveItem(id, parentId);
      } catch (retryErr) {
        console.error(
          '[useMoveItem] retry-after-encrypt failed for item',
          id,
          '→',
          parentId,
          retryErr,
        );
        throw retryErr;
      }
    }
  };

  return useMutation({
    mutationFn: async (payload: MoveItemPayload) => {
      // Sequential to keep modal UX one-at-a-time and to keep
      // backend lock contention down on the parent rows.
      for (const id of payload.ids) {
        await moveOne(id, payload.parentId);
      }
    },
    onMutate: async (payload: MoveItemPayload) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic updates
      await queryClient.cancelQueries({
        queryKey: ["items", payload.oldParentId, "children"],
      });

      await queryClient.cancelQueries({
        queryKey: ["items", payload.parentId, "children"],
      });
    },
    onSuccess: (data, payload: MoveItemPayload) => {
      removeItems(["items", payload.oldParentId], payload.ids);
      removeItems(getMyFilesQueryKey(), payload.ids);
      removeItems(getSharedWithMeQueryKey(), payload.ids);
      removeItems(getRecentItemsQueryKey(), payload.ids);
      queryClient.invalidateQueries({
        queryKey: ["items", payload.parentId],
      });
    },
    onError: (err, variables) => {
      // If the mutation fails, you could invalidate to ensure fresh data
      queryClient.invalidateQueries({
        queryKey: ["items", variables.oldParentId, "children", "infinite"],
      });

      queryClient.invalidateQueries({
        queryKey: ["items", variables.parentId, "children", "infinite"],
      });
    },
  });
};
