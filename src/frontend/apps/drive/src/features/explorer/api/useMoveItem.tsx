import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export const useMoveItems = (itemId: string) => {
  type MoveItemPayload = {
    ids: string[];
    parentId: string;
  };

  const queryClient = useQueryClient();
  const driver = getDriver();
  return useMutation({
    mutationFn: async (payload: MoveItemPayload) => {
      console.log("payload", payload);
      await driver.moveItems(payload.ids, payload.parentId);
    },
    onMutate: async (payload: MoveItemPayload) => {
      const itemIds = payload.ids;
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ["items", itemId, "children"],
      });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData([
        "items",
        itemId,
        "children",
      ]);

      // Optimistically update to the new value
      queryClient.setQueryData(["items", itemId, "children"], (old: Item[]) =>
        old ? old.filter((i: Item) => !itemIds.includes(i.id)) : old
      );

      // Return a context object with the snapshotted value
      return { previousItems };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      queryClient.setQueryData(
        ["items", itemId, "children"],
        context?.previousItems
      );
    },
    // onSuccess: () => {
    //   queryClient.invalidateQueries({
    //     queryKey: ["items", item!.id],
    //   });
    // },
  });
};
