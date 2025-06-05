import { getDriver } from "@/features/config/Config";
import { Item, ItemType } from "@/features/drivers/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export const useMoveItems = () => {
  type MoveItemPayload = {
    ids: string[];
    parentId: string;
    oldParentId: string;
  };

  const queryClient = useQueryClient();
  const driver = getDriver();
  return useMutation({
    mutationFn: async (payload: MoveItemPayload) => {
      await driver.moveItems(payload.ids, payload.parentId);
    },
    onMutate: async (payload: MoveItemPayload) => {
      const itemIds = payload.ids;
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ["items", payload.oldParentId, "children"],
      });

      await queryClient.cancelQueries({
        queryKey: ["items", payload.parentId, "children"],
      });

      // Snapshot the previous value
      const previousItems: Item[] =
        queryClient.getQueryData(["items", payload.oldParentId, "children"]) ??
        [];

      const nextItems: Item[] =
        queryClient.getQueryData(["items", payload.parentId, "children"]) ?? [];

      // Get the nodes from previous items that match the ids
      const movedItems = previousItems?.filter((item: Item) =>
        itemIds.includes(item.id)
      );

      const newOldParentItems = previousItems?.filter(
        (item: Item) => !itemIds.includes(item.id)
      );

      const newNextItems = [...movedItems, ...nextItems];

      // Sort newNextItems by type first (folders first), then by creation date in descending order
      newNextItems.sort((a, b) => {
        // First sort by type (folders first)
        if (a.type !== b.type) {
          return a.type === ItemType.FOLDER ? -1 : 1;
        }

        // Then sort by creation date in descending order (newest first)
        const dateA = new Date(a.created_at || 0).getTime();
        const dateB = new Date(b.created_at || 0).getTime();
        return dateB - dateA;
      });

      // Optimistically update to the new value
      queryClient.setQueryData(
        ["items", payload.oldParentId, "children"],
        () => newOldParentItems
      );

      queryClient.setQueryData(
        ["items", payload.parentId, "children"],
        () => newNextItems
      );

      // Return a context object with the snapshotted value
      return { previousItems, nextItems };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      queryClient.setQueryData(
        ["items", variables.oldParentId, "children"],
        context?.previousItems
      );

      queryClient.setQueryData(
        ["items", variables.parentId, "children"],
        context?.nextItems
      );
    },
  });
};
