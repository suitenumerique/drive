import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { useState, useMemo } from "react";
import { useInfiniteItems } from "@/features/explorer/hooks/useInfiniteItems";

export type WorkspacesExplorerProps = {
  readonly defaultFilters: ItemFilters;
  readonly showFilters?: boolean;
};
export default function WorkspacesExplorer({
  defaultFilters,
  showFilters = true,
}: WorkspacesExplorerProps) {
  const [filters, setFilters] = useState<ItemFilters>(defaultFilters);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } =
    useInfiniteItems(filters);

  // Flatten all pages into a single array of items
  const itemChildren = useMemo(() => {
    return data?.pages.flatMap((page) => page.children) ?? [];
  }, [data]);

  return (
    <AppExplorer
      childrenItems={itemChildren}
      filters={filters}
      onFiltersChange={setFilters}
      hasNextPage={hasNextPage}
      showFilters={showFilters}
      isFetchingNextPage={isFetchingNextPage}
      fetchNextPage={fetchNextPage}
      isLoading={isLoading}
    />
  );
}
