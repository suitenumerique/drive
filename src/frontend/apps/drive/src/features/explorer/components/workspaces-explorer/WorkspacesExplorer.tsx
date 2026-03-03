import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { useState, useMemo } from "react";
import { useInfiniteItems } from "@/features/explorer/hooks/useInfiniteItems";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { getFromRoute } from "@/features/explorer/utils/utils";

export type WorkspacesExplorerProps = {
  readonly defaultFilters: ItemFilters;
  readonly showFilters?: boolean;
};
export default function WorkspacesExplorer({
  defaultFilters,
  showFilters = true,
}: WorkspacesExplorerProps) {
  const [filters, setFilters] = useState<ItemFilters>(defaultFilters);

  const viewConfigKey =
    (getFromRoute() as DefaultRoute | null) ?? DefaultRoute.MY_FILES;

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isPlaceholderData,
  } = useInfiniteItems(filters);

  // Flatten all pages into a single array of items
  const itemChildren = useMemo(() => {
    return data?.pages.flatMap((page) => page.children) ?? [];
  }, [data]);

  return (
    <AppExplorer
      key={viewConfigKey}
      viewConfigKey={viewConfigKey}
      defaultBaseFilters={defaultFilters}
      onComputedFiltersChange={setFilters}
      childrenItems={itemChildren}
      hasNextPage={hasNextPage}
      showFilters={showFilters}
      isFetchingNextPage={isFetchingNextPage}
      fetchNextPage={fetchNextPage}
      isLoading={isLoading || isPlaceholderData}
    />
  );
}
