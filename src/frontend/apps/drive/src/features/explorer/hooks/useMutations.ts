import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useExplorer } from "../components/ExplorerContext";

export const useMutationCreateFile = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.createFile>) => {
      return driver.createFile(...payload);
    },
    onSuccess: (data, variables) => {
      if (variables.parentId) {
        queryClient.invalidateQueries({
          queryKey: ["items", variables.parentId],
        });
      }
    },
  });
};

export const useMutationDeleteItems = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  const { item } = useExplorer();
  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.deleteItems>) => {
      await driver.deleteItems(...payload);
    },
    onMutate: async (itemIds) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ["items", item!.id, "children"],
      });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData([
        "items",
        item!.id,
        "children",
      ]);

      // Optimistically update to the new value
      queryClient.setQueryData(["items", item!.id, "children"], (old: Item[]) =>
        old ? old.filter((i: Item) => !itemIds.includes(i.id)) : old
      );

      // Return a context object with the snapshotted value
      return { previousItems };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      queryClient.setQueryData(
        ["items", item!.id, "children"],
        context?.previousItems
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", item!.id],
      });
    },
  });
};

export const useMutationRenameItem = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  const { item } = useExplorer();
  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.updateItem>) => {
      await driver.updateItem(...payload);
    },
    onMutate: async (itemUpdated) => {
      await queryClient.cancelQueries({
        queryKey: ["items", item!.id, "children"],
      });
      const previousItems = queryClient.getQueryData([
        "items",
        item!.id,
        "children",
      ]);
      queryClient.setQueryData(["items", item!.id, "children"], (old: Item[]) =>
        old
          ? old.map((i: Item) =>
              i.id === itemUpdated.id ? { ...i, ...itemUpdated } : i
            )
          : old
      );
      return { previousItems };
    },
    onError: (err, variables, context) => {
      queryClient.setQueryData(
        ["items", item!.id, "children"],
        context?.previousItems
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", item!.id, "children"],
      });
    },
  });
};

export const useMutationCreateFolder = () => {
  const queryClient = useQueryClient();
  const driver = getDriver();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createFolder>) => {
      return driver.createFolder(...payload);
    },
    onSuccess: (data, variables) => {
      if (variables.parentId) {
        queryClient.invalidateQueries({
          queryKey: ["items", variables.parentId],
        });
      }
    },
  });
};
