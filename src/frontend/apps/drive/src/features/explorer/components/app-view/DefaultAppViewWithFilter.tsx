import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { useState, useMemo } from "react";
import { useInfiniteItems } from "@/features/explorer/hooks/useInfiniteItems";

export type DefaultAppViewWithFilterProps = {
  defaultFilters: ItemFilters;
};
export default function DefaultAppViewWithFilter({
  defaultFilters,
}: {
  defaultFilters: ItemFilters;
}) {
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
      isFetchingNextPage={isFetchingNextPage}
      fetchNextPage={fetchNextPage}
      isLoading={isLoading}
    />
  );
}
