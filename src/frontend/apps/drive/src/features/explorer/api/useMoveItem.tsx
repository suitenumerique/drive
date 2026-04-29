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
   * the driver can't handle in-line: plaintext → encrypted folder.
   * The driver throws `MoveRequiresEncryption('plaintext-into-encrypted')`;
   * we route the request through the recursive-encryption modal in
   * encrypt-on-move mode. That modal does encryption AND the move in a
   * single atomic backend call (POST /move/ with the encrypt-on-move
   * payload), so there is NO retry afterwards — `requestEncryption`
   * resolving means both happened.
   *
   * The encrypt-on-move route avoids the "encrypt-in-place then demote"
   * sequence's main waste: that flow materialised ItemAccess rows for
   * every inherited collaborator at the source location, then preserved
   * those rows after demoting into the chain (so the chain user the
   * file ended up under inherited a pile of stale per-user wraps from
   * users that had nothing to do with the destination tree). The
   * encrypt-on-move path produces a chain-rooted item with no per-user
   * wraps anywhere — clean state on arrival.
   *
   * Other cross-boundary cases are still handled by the driver itself:
   *   - encrypted → encrypted (same root): in-line rewrap.
   *   - encrypted → plaintext / workspace root: in-line re-anchor.
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
      // Encrypt-on-move requires a destination (the chain to attach
      // under). Workspace-root has no chain, so a plaintext-into-root
      // move shouldn't reach here anyway — defensively throw if it does.
      if (!parentId) {
        throw new Error(
          'plaintext-into-encrypted reported without a destination — driver bug.',
        );
      }
      const item = await driver.getItem(id);
      try {
        await requestEncryption(item, { intoChainParentId: parentId });
      } catch (modalErr) {
        if (modalErr instanceof EncryptionRequestCancelled) {
          return; // User closed the modal — abort the move silently.
        }
        throw modalErr;
      }
      // No retry: encrypt-on-move's commit IS the move.
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
