import { Item } from "@/features/drivers/types";
import { PaginatedChildrenResult } from "@gouvfr-lasuite/ui-kit";
import { QueryClient, QueryKey, useQueryClient } from "@tanstack/react-query";

/**
 * Adds an item to the top of the first page of a paginated infinite query list.
 * This function finds all queries matching the queryKey pattern and updates them
 * by prepending the new item to the first page.
 *
 * @param queryClient - The react-query QueryClient instance
 * @param queryKey - The query key pattern to match (can be partial)
 * @param newItem - The item to add at the top of the list
 */
export const addItemToTopOfPaginatedList = (
  queryClient: QueryClient,
  queryKey: QueryKey,
  newItem: Item
): void => {
  // Get all queries matching the queryKey pattern
  const queriesData = queryClient.getQueriesData({
    queryKey,
  });

  queriesData.forEach((query) => {
    const key = query[0];
    const data = query[1] as
      | { pages: PaginatedChildrenResult<Item>[] }
      | undefined;

    if (!data || !data.pages || data.pages.length === 0) {
      return;
    }

    // Deep clone to avoid mutating the original data
    const updatedData: { pages: PaginatedChildrenResult<Item>[] } = JSON.parse(
      JSON.stringify(data)
    );

    // Add the new item to the top of the first page
    if (updatedData.pages[0]) {
      // Check if item already exists to avoid duplicates
      const itemExists = updatedData.pages.some((page) =>
        page.children?.some((child) => child.id === newItem.id)
      );

      if (!itemExists) {
        updatedData.pages[0].children = [
          newItem,
          ...(updatedData.pages[0].children || []),
        ];
      }
    }

    // Update the query data
    queryClient.setQueryData(key, updatedData);
  });
};

/**
 * Removes items from a paginated infinite query list.
 * This function finds all queries matching the queryKey pattern and updates them
 * by filtering out the items with the specified IDs from all pages.
 *
 * @param queryClient - The react-query QueryClient instance
 * @param queryKey - The query key pattern to match (can be partial)
 * @param itemIds - The IDs of items to remove from the list
 */
export const removeItemsFromPaginatedList = (
  queryClient: QueryClient,
  queryKey: QueryKey,
  itemIds: string[]
): void => {
  // Get all queries matching the queryKey pattern
  const queriesData = queryClient.getQueriesData({
    queryKey,
  });

  queriesData.forEach((query) => {
    const key = query[0];
    const data = query[1] as
      | { pages: PaginatedChildrenResult<Item>[] }
      | undefined;

    if (!data || !data.pages || data.pages.length === 0) {
      return;
    }

    // Deep clone to avoid mutating the original data
    const updatedData: { pages: PaginatedChildrenResult<Item>[] } = JSON.parse(
      JSON.stringify(data)
    );

    // Remove items from all pages
    updatedData.pages.forEach((page) => {
      page.children = page.children?.filter(
        (child) => !itemIds.includes(child.id)
      );
    });

    // Update the query data
    queryClient.setQueryData(key, updatedData);
  });
};

/**
 * Hook that returns a function to add an item to the top of a paginated list.
 * This is a convenience hook that provides access to the queryClient.
 *
 * @example
 * ```tsx
 * const addItemToTop = useAddItemToPaginatedList();
 *
 * // In a mutation's onSuccess callback:
 * onSuccess: (newItem) => {
 *   addItemToTop(
 *     ["items", parentId, "children", "infinite"],
 *     newItem
 *   );
 * }
 * ```
 *
 * @returns A function that takes a queryKey and an item, and adds the item to the top of the list
 */
export const useAddItemToPaginatedList = () => {
  const queryClient = useQueryClient();

  return (queryKey: QueryKey, newItem: Item) => {
    addItemToTopOfPaginatedList(queryClient, queryKey, newItem);
  };
};

/**
 * Hook that returns a function to remove items from a paginated list.
 * This is a convenience hook that provides access to the queryClient.
 *
 * @example
 * ```tsx
 * const removeItems = useRemoveItemsFromPaginatedList();
 *
 * // In a mutation's onSuccess callback:
 * onSuccess: () => {
 *   removeItems(
 *     ["items", parentId, "children", "infinite"],
 *     ["item-id-1", "item-id-2"]
 *   );
 * }
 * ```
 *
 * @returns A function that takes a queryKey and item IDs, and removes those items from the list
 */
export const useRemoveItemsFromPaginatedList = () => {
  const queryClient = useQueryClient();

  return (queryKey: QueryKey, itemIds: string[]) => {
    removeItemsFromPaginatedList(queryClient, queryKey, itemIds);
  };
};

/**
 * Updates a partial item in a paginated infinite query list.
 * This function finds all queries matching the queryKey pattern and updates them
 * by merging the partial update with the existing item in all pages.
 *
 * @param queryClient - The react-query QueryClient instance
 * @param queryKey - The query key pattern to match (can be partial)
 * @param itemId - The ID of the item to update
 * @param partialUpdate - The partial item data to merge with the existing item
 */
export const updateItemInPaginatedList = (
  queryClient: QueryClient,
  queryKey: QueryKey,
  itemId: string,
  partialUpdate: Partial<Item>
): void => {
  // Get all queries matching the queryKey pattern
  const queriesData = queryClient.getQueriesData({
    queryKey,
  });

  queriesData.forEach((query) => {
    const key = query[0];
    const data = query[1] as
      | { pages: PaginatedChildrenResult<Item>[] }
      | undefined;

    if (!data || !data.pages || data.pages.length === 0) {
      return;
    }

    // Deep clone to avoid mutating the original data
    const updatedData: { pages: PaginatedChildrenResult<Item>[] } = JSON.parse(
      JSON.stringify(data)
    );

    // Update item in all pages
    updatedData.pages.forEach((page) => {
      if (page.children) {
        page.children = page.children.map((child) =>
          child.id === itemId ? { ...child, ...partialUpdate } : child
        );
      }
    });

    // Update the query data
    queryClient.setQueryData(key, updatedData);
  });
};

/**
 * Hook that returns a function to update a partial item in a paginated list.
 * This is a convenience hook that provides access to the queryClient.
 *
 * @example
 * ```tsx
 * const updateItem = useUpdateItemInPaginatedList();
 *
 * // In a mutation's onSuccess callback:
 * onSuccess: (updatedItem) => {
 *   updateItem(
 *     ["items", parentId, "children", "infinite"],
 *     updatedItem.id,
 *     { title: updatedItem.title, is_favorite: updatedItem.is_favorite }
 *   );
 * }
 * ```
 *
 * @returns A function that takes a queryKey, itemId, and partial update, and updates the item in the list
 */
export const useUpdateItemInPaginatedList = () => {
  const queryClient = useQueryClient();

  return (queryKey: QueryKey, itemId: string, partialUpdate: Partial<Item>) => {
    updateItemInPaginatedList(queryClient, queryKey, itemId, partialUpdate);
  };
};
