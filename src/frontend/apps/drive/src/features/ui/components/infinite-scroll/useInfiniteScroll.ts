import {
  useInfiniteQuery,
  UseInfiniteQueryResult,
} from "@tanstack/react-query";

interface UseInfiniteScrollOptions<T> {
  /** Query key for React Query */
  queryKey: (string | number | boolean | object)[];
  /** Function to fetch data for a specific page */
  queryFn: ({ pageParam }: { pageParam: number }) => Promise<T[]>;
  /** Whether the query is enabled */
  enabled?: boolean;
  /** Page size for determining if there are more pages */
  pageSize?: number;
}

interface UseInfiniteScrollReturn<T> {
  /** All items from all pages flattened into a single array */
  items: T[];
  /** Whether there are more pages to load */
  hasNextPage: boolean;
  /** Whether currently fetching the next page */
  isFetchingNextPage: boolean;
  /** Function to load the next page */
  fetchNextPage: () => void;
  /** Whether the initial query is loading */
  isLoading: boolean;
  /** Whether there was an error */
  isError: boolean;
  /** Error object if there was an error */
  error: Error | null;
  /** Refetch all data */
  refetch: () => void;
}

/**
 * Custom hook that combines useInfiniteQuery with infinite scroll logic.
 *
 * This hook simplifies the usage of InfiniteScroll component by providing
 * all the necessary props and flattening the paginated data.
 *
 * @param options Configuration options for the infinite query
 * @returns Object with items, loading states, and control functions
 */
export const useInfiniteScroll = <T>({
  queryKey,
  queryFn,
  enabled = true,
  pageSize = 20,
}: UseInfiniteScrollOptions<T>): UseInfiniteScrollReturn<T> => {
  const query: UseInfiniteQueryResult<T[], Error> = useInfiniteQuery({
    queryKey,
    queryFn,
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      // If the last page has fewer items than the page size, we've reached the end
      if (lastPage.length < pageSize) {
        return undefined;
      }
      return allPages.length + 1;
    },
    enabled,
  });

  // Flatten all pages into a single array
  const items = query.data?.pages.flat() ?? [];

  return {
    items,
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    fetchNextPage: query.fetchNextPage,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
};
