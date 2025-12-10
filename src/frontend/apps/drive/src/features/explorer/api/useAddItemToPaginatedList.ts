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
