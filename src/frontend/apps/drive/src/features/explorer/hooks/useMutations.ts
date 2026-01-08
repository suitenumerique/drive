import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { useMutation, useQueryClient, QueryKey } from "@tanstack/react-query";
import { useGlobalExplorer } from "../components/GlobalExplorerContext";
import {
  useAddItemToPaginatedList,
  useRemoveItemsFromPaginatedList,
  useUpdateItemInPaginatedList,
} from "../api/useManageItemsToPaginatedList";
import { useRouter } from "next/router";
import { getQueryKeyForRouteId, isMyFilesRoute } from "@/utils/defaultRoutes";
import {
  PaginatedChildrenResult,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { getParentIdFromPath } from "../utils/utils";

export const useMutationCreateFile = () => {
  const driver = getDriver();
  const refresh = useRefreshQueryCacheAfterMutation();

  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.createFile>) => {
      return driver.createFile(...payload);
    },
    onSuccess: (data, variables) => {
      refresh(variables.parentId);
    },
    meta: {
      showErrorOn403: true,
    },
  });
};

export const useMutationDeleteItems = () => {
  const driver = getDriver();
  const { item } = useGlobalExplorer();
  const parentId = getParentIdFromPath(item?.path);
  const mutationCallbacks = useDeleteMutationCallbacks(parentId);

  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.deleteItems>) => {
      await driver.deleteItems(...payload);
    },
    ...mutationCallbacks,
  });
};

export const useMutationHardDeleteItems = () => {
  const driver = getDriver();
  const mutationCallbacks = useDeleteMutationCallbacks(undefined, [
    "items",
    "trash",
  ]);

  return useMutation({
    mutationFn: async (
      ...payload: Parameters<typeof driver.hardDeleteItems>
    ) => {
      await driver.hardDeleteItems(...payload);
    },
    ...mutationCallbacks,
  });
};

export const useMutationRenameItem = () => {
  const driver = getDriver();

  const { item } = useGlobalExplorer();
  const { onMutate, onError } = useUpdateMutationCallbacks(item?.id);
  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.updateItem>) => {
      await driver.updateItem(...payload);
    },
    onMutate,
    onError,
  });
};

export const useMutationCreateFolder = () => {
  const driver = getDriver();
  const addItemToTopOfPaginatedList = useAddItemToPaginatedList();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createFolder>) => {
      return driver.createFolder(...payload);
    },
    onSuccess: (data, variables) => {
      const queryKey = variables.parentId
        ? ["items", variables.parentId, "children"]
        : ["items", "infinite", JSON.stringify({ is_creator_me: true })];
      addItemToTopOfPaginatedList(queryKey, data);

      queryClient.invalidateQueries({
        queryKey: ["rootItems"],
      });
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

export const useMutationUpdateLinkConfiguration = () => {
  const driver = getDriver();
  const refreshItemCache = useRefreshItemCache();
  return useMutation({
    mutationFn: async (
      ...payload: Parameters<typeof driver.updateLinkConfiguration>
    ) => {
      await driver.updateLinkConfiguration(...payload);
    },
    onSuccess: (_, variables) => {
      refreshItemCache(variables.itemId);
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

const useOnSuccessAccessOrInvitationMutation = () => {
  const queryClient = useQueryClient();
  const refreshItemCache = useRefreshItemCache();
  return (itemId: string, isInvitation: boolean = false) => {
    refreshItemCache(itemId);
    queryClient.invalidateQueries({
      queryKey: ["items", itemId, "children"],
    });

    if (isInvitation) {
      queryClient.invalidateQueries({
        queryKey: ["itemInvitations", itemId],
      });
    } else {
      queryClient.invalidateQueries({
        queryKey: ["itemAccesses", itemId],
      });
    }
  };
};

export const useMutationCreateAccess = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createAccess>) => {
      return driver.createAccess(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
    },
  });
};

export const useMutationCreateInvitation = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createInvitation>) => {
      return driver.createInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, true);
    },
  });
};

export const useMutationUpdateInvitation = () => {
  const driver = getDriver();

  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.updateInvitation>) => {
      return driver.updateInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, true);
    },
  });
};

export const useMutationUpdateAccess = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.updateAccess>) => {
      return driver.updateAccess(...payload);
    },
    onSuccess: (_data, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
    },
  });
};

export const useMutationDeleteAccess = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteAccess>) => {
      return driver.deleteAccess(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
    },
  });
};

export const useMutationDeleteInvitation = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteInvitation>) => {
      return driver.deleteInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, true);
    },
  });
};

export const useRefreshFavoriteCache = () => {
  const updateItemInPaginatedList = useUpdateItemInPaginatedList();
  const queryClient = useQueryClient();
  return (itemId: string, isFavorite: boolean) => {
    const partialUpdate: Partial<Item> = {
      is_favorite: isFavorite,
    };
    updateItemInPaginatedList(["items"], itemId, partialUpdate);
    queryClient.invalidateQueries({
      queryKey: ["items", "infinite", JSON.stringify({ is_favorite: true })],
    });

    queryClient.setQueryData(["item", itemId], (old: Item) => {
      return {
        ...old,
        is_favorite: isFavorite,
      };
    });
  };
};

export const useMutationCreateFavoriteItem = () => {
  const driver = getDriver();

  const refreshFavoriteCache = useRefreshFavoriteCache();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createFavoriteItem>) => {
      return driver.createFavoriteItem(...payload);
    },
    onSuccess: (_, itemId: string) => {
      refreshFavoriteCache(itemId, true);
    },
  });
};

export const useMutationDeleteFavoriteItem = () => {
  const driver = getDriver();
  const treeContext = useTreeContext();
  const refreshFavoriteCache = useRefreshFavoriteCache();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteFavoriteItem>) => {
      return driver.deleteFavoriteItem(...payload);
    },
    onSuccess: (_data, itemId: string) => {
      // We add the path level to the id to avoid conflicts with the same id inside the tree for favorite items.
      treeContext?.treeData.deleteNode(itemId + "_0");
      refreshFavoriteCache(itemId, false);
    },
  });
};

export const useGetQueryKey = () => {
  const router = useRouter();
  return (parentId?: string) => {
    const isOnMyFilesRoute = isMyFilesRoute(router.pathname);
    let queryKey = parentId ? ["items", parentId, "children"] : [];
    if (isOnMyFilesRoute) {
      queryKey = getQueryKeyForRouteId(router.pathname);
    }
    return queryKey;
  };
};

export const useRemoveFromQueryCache = () => {
  const getQueryKey = useGetQueryKey();
  const queryClient = useQueryClient();
  const removeItems = useRemoveItemsFromPaginatedList();

  return async (itemIds: string[], parentId?: string) => {
    const queryKey = getQueryKey(parentId);
    await queryClient.cancelQueries({
      queryKey,
    });
    const previousItems = queryClient.getQueryData(queryKey);
    removeItems(queryKey, itemIds);

    return { previousItems };
  };
};

export const useRefreshQueryCacheAfterMutation = () => {
  const queryClient = useQueryClient();
  const getQueryKey = useGetQueryKey();

  return (parentId?: string) => {
    const queryKey = getQueryKey(parentId);
    const previousItems = queryClient.getQueryData(queryKey);
    queryClient.invalidateQueries({
      queryKey,
    });
    return { previousItems };
  };
};

export const useDeleteMutationCallbacks = (
  parentId?: string,
  defaultQueryKey?: string[]
) => {
  const queryClient = useQueryClient();
  const getQueryKey = useGetQueryKey();
  const removeItems = useRemoveItemsFromPaginatedList();
  const queryKey = defaultQueryKey ?? getQueryKey(parentId);

  const onMutate = async (itemIds: string[]) => {
    await queryClient.cancelQueries({
      queryKey,
    });
    const previousItems = queryClient.getQueryData(queryKey);
    removeItems(queryKey, itemIds);
    return { previousItems };
  };

  const onError = (_err: unknown, _variables: unknown, context: unknown) => {
    queryClient.setQueryData(
      queryKey,
      (context as { previousItems: Item[] })?.previousItems
    );
  };

  const onSuccess = () => {
    if (queryKey.length === 0) {
      return;
    }
    console.log("onSuccess", queryKey);
    queryClient.invalidateQueries({
      queryKey,
    });
  };

  return { onMutate, onError, onSuccess };
};

export const useUpdateMutationCallbacks = (
  parentId?: string,
  defaultQueryKey?: string[]
) => {
  const queryClient = useQueryClient();
  const getQueryKey = useGetQueryKey();
  const queryKey = defaultQueryKey ?? getQueryKey(parentId);

  const onMutate = async (itemUpdated: Partial<Item>) => {
    if (!itemUpdated.id) {
      return {};
    }

    await queryClient.cancelQueries({
      queryKey,
    });

    // Get all queries matching the queryKey pattern
    const queriesData = queryClient.getQueriesData({
      queryKey,
    });

    const previousData: Array<[QueryKey, unknown]> = [];

    queriesData.forEach((query) => {
      const key = query[0] as QueryKey;
      const data = query[1] as
        | { pages: PaginatedChildrenResult<Item>[] }
        | undefined;

      // Store previous data for rollback
      previousData.push([key, data]);

      if (!data || !data.pages || data.pages.length === 0) {
        return;
      }

      // Deep clone to avoid mutating the original data
      const updatedData: { pages: PaginatedChildrenResult<Item>[] } =
        JSON.parse(JSON.stringify(data));

      // Update item in all pages
      updatedData.pages.forEach((page) => {
        if (page.children) {
          page.children = page.children.map((child) =>
            child.id === itemUpdated.id ? { ...child, ...itemUpdated } : child
          );
        }
      });

      // Update the query data
      queryClient.setQueryData(key, updatedData);
    });

    return { previousData };
  };

  const onError = (_err: unknown, _variables: unknown, context: unknown) => {
    const previousData = (
      context as { previousData?: Array<[QueryKey, unknown]> }
    )?.previousData;

    if (previousData) {
      previousData.forEach(([key, data]) => {
        queryClient.setQueryData(key, data);
      });
    }
  };

  const onSuccess = () => {
    queryClient.invalidateQueries({
      queryKey,
    });
  };

  return { onMutate, onError, onSuccess };
};

export const useRefreshItemCache = () => {
  const queryClient = useQueryClient();
  const driver = getDriver();
  const updateItemInPaginatedList = useUpdateItemInPaginatedList();
  return async (itemId: string, partialUpdate?: Partial<Item>) => {
    if (partialUpdate) {
      updateItemInPaginatedList(["items"], itemId, partialUpdate);
      queryClient.setQueryData(["item", itemId], (old: Item) => {
        return {
          ...old,
          ...partialUpdate,
        };
      });
    } else {
      const item = await driver.getItem(itemId);
      queryClient.setQueryData(["item", itemId], item);
      updateItemInPaginatedList(["items"], itemId, item);
    }
  };
};
