import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useGlobalExplorer,
  generateTreeId,
} from "../components/GlobalExplorerContext";
import {
  useAddItemToPaginatedList,
  useRemoveItemsFromPaginatedList,
} from "./useOptimisticPagination";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import {
  useRefreshQueryCacheAfterMutation,
  useDeleteMutationCallbacks,
  useRefreshItemCache,
  useRefreshFavoriteCache,
} from "./useRefreshItems";
import { DefaultRoute } from "@/utils/defaultRoutes";

// ============================================================================
// MUTATIONS
// ============================================================================

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

  const mutationCallbacks = useDeleteMutationCallbacks(
    item?.originalId ?? item?.id,
  );

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
    ["items", "trash"],
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
  const refreshItemCache = useRefreshItemCache();

  return useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.updateItem>) => {
      await driver.updateItem(...payload);
    },
    onMutate: async (...payload: Parameters<typeof driver.updateItem>) => {
      if (!payload[0].id) {
        return;
      }
      await refreshItemCache(payload[0].id!, { title: payload[0].title });
    },
    onError: (_error, variables) => {
      if (!variables.id) {
        return;
      }

      refreshItemCache(variables.id);
    },

    onSuccess: (_, itemUpdated) => {
      if (!itemUpdated?.id) {
        return;
      }
      refreshItemCache(itemUpdated.id, itemUpdated);
    },
  });
};

export const useMutationCreateFolder = () => {
  const driver = getDriver();
  const addItemToTopOfPaginatedList = useAddItemToPaginatedList();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createFolder>) => {
      return driver.createFolder(...payload);
    },
    onSuccess: (data, variables) => {
      const queryKey = variables.parentId
        ? ["items", variables.parentId, "children"]
        : ["items", "infinite", JSON.stringify({ is_creator_me: true })];
      addItemToTopOfPaginatedList(queryKey, data);
    },
  });
};

export const useMutationUpdateLinkConfiguration = () => {
  const driver = getDriver();
  const refreshItemCache = useRefreshItemCache();
  const queryClient = useQueryClient();
  const refreshQueryCacheAfterMutation = useRefreshQueryCacheAfterMutation();
  return useMutation({
    mutationFn: async (
      ...payload: Parameters<typeof driver.updateLinkConfiguration>
    ) => {
      await driver.updateLinkConfiguration(...payload);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["items", variables.itemId],
      });

      queryClient.invalidateQueries({
        queryKey: ["itemAccesses"],
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

export const useMutationCreateFavoriteItem = () => {
  const driver = getDriver();

  const refreshFavoriteCache = useRefreshFavoriteCache();
  const refreshItemCache = useRefreshItemCache();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createFavoriteItem>) => {
      return driver.createFavoriteItem(...payload);
    },
    onSuccess: (_, itemId: string) => {
      refreshFavoriteCache(itemId, true);
      refreshItemCache(itemId, { is_favorite: true });
    },
  });
};

export const useMutationDeleteFavoriteItem = () => {
  const driver = getDriver();
  const treeContext = useTreeContext();
  const removeItems = useRemoveItemsFromPaginatedList();
  const refreshFavoriteCache = useRefreshFavoriteCache();
  const refreshItemCache = useRefreshItemCache();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteFavoriteItem>) => {
      return driver.deleteFavoriteItem(...payload);
    },
    onSuccess: (_data, itemId: string) => {
      // Only delete the root favorite node (directly under favorites)
      // Children of opened favorite folders should remain visible
      const rootFavoriteTreeId = generateTreeId(
        itemId,
        DefaultRoute.FAVORITES,
        true,
      );
      treeContext?.treeData.deleteNode(rootFavoriteTreeId);
      removeItems(
        ["items", "infinite", JSON.stringify({ is_favorite: true })],
        [itemId],
      );
      refreshItemCache(itemId, { is_favorite: false });
      refreshFavoriteCache(itemId, false);
    },
  });
};
