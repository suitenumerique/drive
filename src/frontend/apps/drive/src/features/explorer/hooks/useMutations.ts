import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useGlobalExplorer } from "../components/GlobalExplorerContext";

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
  const { item } = useGlobalExplorer();
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
      queryClient.setQueryData(
        ["items", item!.id, "children"],
        (old: Item[]) =>
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

export const useMutationHardDeleteItems = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      ...payload: Parameters<typeof driver.hardDeleteItems>
    ) => {
      await driver.hardDeleteItems(...payload);
    },
    onMutate: async (itemIds) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ["items", "trash"],
      });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData(["items", "trash"]);

      // Optimistically update to the new value
      queryClient.setQueryData(["items", "trash"], (old: Item[]) =>
        old ? old.filter((i: Item) => !itemIds.includes(i.id)) : old
      );

      // Return a context object with the snapshotted value
      return { previousItems };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      queryClient.setQueryData(["items", "trash"], context?.previousItems);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", "trash"],
      });
    },
  });
};

export const useMutationRenameItem = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  const { item } = useGlobalExplorer();
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
      queryClient.setQueryData(
        ["items", item!.id, "children"],
        (old: Item[]) =>
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

export const useMutationUpdateItem = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  const { item } = useGlobalExplorer();
  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.updateItem>) => {
      await driver.updateItem(...payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", item!.id],
        exact: true,
      });
    },
  });
};

export const useMutationRestoreItems = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.restoreItems>) => {
      await driver.restoreItems(...payload);
    },
    onMutate: async (ids) => {
      await queryClient.cancelQueries({ queryKey: ["items", "trash"] });
      const previousItems = queryClient.getQueryData<Item[]>([
        "items",
        "trash",
      ]);
      queryClient.setQueryData<Item[]>(["items", "trash"], (old) => {
        return old?.filter((item) => !ids.includes(item.id)) ?? [];
      });
      return { previousItems };
    },
    onError: (err, variables, context) => {
      queryClient.setQueryData(["items", "trash"], context?.previousItems);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", "trash"],
      });
    },
  });
};

export const useMutationCreateWorskpace = () => {
  const queryClient = useQueryClient();
  const driver = getDriver();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createWorkspace>) => {
      return driver.createWorkspace(...payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items"],
      });
    },
  });
};

// TODO: Make optimistic once the tree is implemented
export const useMutationUpdateWorkspace = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      ...payload: Parameters<typeof driver.updateWorkspace>
    ) => {
      await driver.updateWorkspace(...payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items"],
      });
    },
  });
};

// TODO: Make optimistic once the tree is implemented
export const useMutationDeleteWorskpace = () => {
  const queryClient = useQueryClient();
  const driver = getDriver();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteWorkspace>) => {
      return driver.deleteWorkspace(...payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items"],
      });
    },
  });
};

export const useMutationCreateAccess = () => {
  const driver = getDriver();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createAccess>) => {
      return driver.createAccess(...payload);
    },
  });
};

export const useMutationCreateInvitation = () => {
  const driver = getDriver();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createInvitation>) => {
      return driver.createInvitation(...payload);
    },
  });
};

export const useMutationUpdateInvitation = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.updateInvitation>) => {
      return driver.updateInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["itemInvitations", variables.itemId],
      });
    },
  });
};

export const useMutationUpdateAccess = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.updateAccess>) => {
      return driver.updateAccess(...payload);
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["itemAccesses", variables.itemId],
      });
    },
  });
};

export const useMutationDeleteAccess = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteAccess>) => {
      return driver.deleteAccess(...payload);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["itemAccesses", variables.itemId],
      });
    },
  });
};

export const useMutationDeleteInvitation = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteInvitation>) => {
      return driver.deleteInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["itemInvitations", variables.itemId],
      });
    },
  });
};
