import { getDriver } from "@/features/config/Config";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRemoveItemsFromPaginatedList } from "./useManageItemsToPaginatedList";
import {
  getMyFilesQueryKey,
  getRecentItemsQueryKey,
  getSharedWithMeQueryKey,
} from "@/utils/defaultRoutes";

export const useMoveItems = () => {
  type MoveItemPayload = {
    ids: string[];
    parentId?: string;
    oldParentId?: string;
  };

  const queryClient = useQueryClient();
  const driver = getDriver();

  const removeItems = useRemoveItemsFromPaginatedList();

  return useMutation({
    mutationFn: async (payload: MoveItemPayload) => {
      await driver.moveItems(payload.ids, payload.parentId);
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
