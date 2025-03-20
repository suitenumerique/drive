import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
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
      console.log("payload", payload);
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

      console.log("payload", payload);
      console.log("previousItems", previousItems);
      console.log("nextItems", nextItems);

      // Récupérer les nœuds du previous item qui correspondent aux ids
      const movedItems = previousItems?.filter((item: Item) =>
        itemIds.includes(item.id)
      );

      const newOldParentItems = previousItems?.filter(
        (item: Item) => !itemIds.includes(item.id)
      );

      const newNextItems = [...nextItems, ...movedItems];
      console.log("movedItems", movedItems);

      // // Ajouter les éléments déplacés dans le nouvel emplacement
      // if (nextItems && movedItems) {
      //   queryClient.setQueryData(
      //     ["items", payload.parentId, "children"],
      //     (old: Item[]) => (old ? [...old, ...movedItems] : movedItems)
      //   );
      // }
      // Optimistically update to the new value
      queryClient.setQueryData(
        ["items", payload.oldParentId, "children"],
        () => newOldParentItems
      );

      queryClient.setQueryData(
        ["items", payload.parentId, "children"],
        () => newNextItems
      );

      // Snapshot the previous value
      const afterOldParentItems: Item[] =
        queryClient.getQueryData(["items", payload.oldParentId, "children"]) ??
        [];

      const afterNextItems: Item[] =
        queryClient.getQueryData(["items", payload.parentId, "children"]) ?? [];

      console.log("afterOldParentItems", afterOldParentItems);
      console.log("afterNextItems", afterNextItems);

      // Return a context object with the snapshotted value
      return { previousItems, nextItems };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      queryClient.setQueryData(
        ["items", variables.oldParentId, "children"],
        context?.previousItems
      );

      console.log("context?.nextItems", context?.nextItems);
      queryClient.setQueryData(
        ["items", variables.parentId, "children"],
        context?.nextItems
      );
    },
    // onSuccess: () => {
    //   queryClient.invalidateQueries({
    //     queryKey: ["items", item!.id],
    //   });
    // },
  });
};
