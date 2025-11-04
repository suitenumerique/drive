import { useEffect, useRef, useCallback, ReactNode } from "react";
import { Loader, useCunningham } from "@openfun/cunningham-react";

interface InfiniteScrollProps {
  /** Whether there are more items to load */
  hasNextPage: boolean;
  /** Whether currently fetching the next page */
  isFetchingNextPage: boolean;
  /** Function to call when more items should be loaded */
  fetchNextPage: () => void;
  /** Children to render */
  children: ReactNode;
  /** Optional loading component to show at the bottom */
  loadingComponent?: ReactNode;
  /** Distance from bottom to trigger loading (in pixels) */
  rootMargin?: string;
  /** Intersection threshold (0-1) */
  threshold?: number;
  /** Additional CSS class for the container */
  className?: string;
}

/**
 * InfiniteScroll component that automatically loads more content when the user
 * scrolls near the bottom of the container.
 *
 * Uses Intersection Observer API to detect when the trigger element comes into view
 * and automatically calls fetchNextPage when more content is available.
 */
export const InfiniteScroll = ({
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  children,
  loadingComponent,
  rootMargin = "300px",
  threshold = 1,
  className,
}: InfiniteScrollProps) => {
  const { t: tc } = useCunningham();
  const loadMoreRef = useRef<HTMLDivElement>(null);

  const handleIntersection = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;

      if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage]
  );

  useEffect(() => {
    const observer = new IntersectionObserver(handleIntersection, {
      threshold,
      rootMargin,
    });

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => {
      if (loadMoreRef.current) {
        observer.unobserve(loadMoreRef.current);
      }
    };
  }, [handleIntersection, threshold, rootMargin]);

  const defaultLoadingComponent = (
    <div className="infinite-scroll__loading-component">
      <Loader size="small" aria-label={tc("components.datagrid.loader_aria")} />
    </div>
  );

  return (
    <div className={className}>
      {children}
      {/* Infinite scroll trigger and loading indicator */}
      <div ref={loadMoreRef} className="infinite-scroll__trigger">
        {isFetchingNextPage && (loadingComponent || defaultLoadingComponent)}
      </div>
    </div>
  );
};
