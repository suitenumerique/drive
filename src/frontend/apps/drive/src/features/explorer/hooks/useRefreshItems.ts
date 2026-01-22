import { useQueryClient, QueryKey } from "@tanstack/react-query";
import { Item } from "@/features/drivers/types";
import {
  useRemoveItemsFromPaginatedList,
  useUpdateItemInPaginatedList,
} from "./useOptimisticPagination";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { generateTreeId } from "../components/GlobalExplorerContext";

export const useGetQueryKeyToRefresh = () => {
  
  return (parentId?: string) => {
    
    const queryKeys = [["items", "infinite"]];
    if (parentId) {
      queryKeys.push(["items", parentId, "children"]);
    }
    // let queryKey = parentId ? ["items", parentId, "children"] : [];
    // if (queryKeyForRoute.length > 0) {
    //   queryKey = queryKeyForRoute;
    // }
    return queryKeys;
  };
};

export const useRefreshQueryCacheAfterMutation = () => {
  const queryClient = useQueryClient();
  const getQueryKey = useGetQueryKeyToRefresh();

  return (parentId?: string) => {
    const queryKey = getQueryKey(parentId);
    
    for (const key of queryKey) {
        queryClient.invalidateQueries({
            queryKey: key,
        });
    }
  };
};

export const useDeleteMutationCallbacks = (
  parentId?: string,
  defaultQueryKey?: string[][]
) => {
  const queryClient = useQueryClient();
  const getQueryKey = useGetQueryKeyToRefresh();
  const removeItems = useRemoveItemsFromPaginatedList();
  const queryKeys = defaultQueryKey ?? getQueryKey(parentId);

  const onMutate = async (itemIds: string[]) => {
    const returnPreviousItems: Map<string[], Item[]> = new Map();
    queryKeys.forEach(async (key) => {
      await queryClient.cancelQueries({
        queryKey: key,
      });
      const previousItems = queryClient.getQueryData<Item[]>(key);
      returnPreviousItems.set(key, previousItems ?? []);
      removeItems(key, itemIds);
    });
   
    return { previousItems: returnPreviousItems };
  };

  const onError = (_err: unknown, _variables: unknown, context: unknown) => {
    const returnPreviousItems = context as { previousItems: Map<string[], Item[]> };
    returnPreviousItems.previousItems.forEach((previousItems, key) => {
      queryClient.setQueryData(key, previousItems);
    });
  };

  const onSuccess = () => {
    if (queryKeys.length === 0) {
      return;
    }

    queryClient.invalidateQueries({
      queryKey: queryKeys,
    });
  };

  return { onMutate, onError, onSuccess };
};

// Explanation:
// The function below is used to refresh the cache for certain queries after a mutation (creation, deletion, update)
// on items/files in the explorer. It takes as an argument the id of the parent whose list of children needs to be refreshed.
// It uses the QueryClient from react-query to force reloading/invalidating queries associated with the parent key:
// - This prevents the UI from becoming out of sync with the backend state after a mutation.
export const useRefreshItemCache = () => {
  const queryClient = useQueryClient();

  const updateItemInPaginatedList = useUpdateItemInPaginatedList();
  return async (
    itemId: string,
    partialUpdate?: Partial<Item>,
    moreQueriesToInvalidate?: QueryKey[]
  ) => {
    if (partialUpdate) {
      updateItemInPaginatedList(["items"], itemId, partialUpdate);
      queryClient.setQueryData(["item", itemId], (old: Item) => {
        return {
          ...old,
          ...partialUpdate,
        };
      });
    } else {
      queryClient.invalidateQueries({
        queryKey: ["items"],
      });
      queryClient.invalidateQueries({
        queryKey: ["item", itemId],
      });
      moreQueriesToInvalidate?.forEach((queryKey) => {
        queryClient.invalidateQueries({
          queryKey,
        });
      });
    }
  };
};

export const useOnSuccessAccessOrInvitationMutation = () => {
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

export const useRefreshFavoriteCache = () => {
  const queryClient = useQueryClient();
  const treeContext = useTreeContext();
  
  return (itemId: string, isFavorite: boolean) => {
    const moreQueriesToInvalidate: QueryKey[] = [
      ["items", "infinite", JSON.stringify({ is_favorite: isFavorite })],
      ["item", itemId],
    ];

  
    const rootFavoriteTreeId = generateTreeId(itemId, DefaultRoute.FAVORITES, true);
    treeContext?.treeData.deleteNode(rootFavoriteTreeId);

    queryClient.invalidateQueries({
      queryKey: moreQueriesToInvalidate,
    });

    
  };
};
