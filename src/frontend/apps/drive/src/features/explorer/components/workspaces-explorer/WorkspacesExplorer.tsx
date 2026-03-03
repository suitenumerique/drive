import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { useState, useMemo } from "react";
import { useInfiniteItems } from "@/features/explorer/hooks/useInfiniteItems";
import { useGridColumns } from "@/features/explorer/hooks/useGridColumns";
import { computeFilters } from "@/features/explorer/utils/ordering";
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
    col1Config,
    col2Config,
    sortState,
    cycleSortForColumn,
    setColumn,
    prefs,
    viewConfig,
  } = useGridColumns(viewConfigKey);

  const finalFilters = useMemo(
    () => computeFilters(viewConfig, filters, sortState),
    [viewConfig, filters, sortState],
  );

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isPlaceholderData,
  } = useInfiniteItems(finalFilters);

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
      isLoading={isLoading || isPlaceholderData}
      sortState={sortState}
      onSort={cycleSortForColumn}
      prefs={prefs}
      onChangeColumn={setColumn}
      col1Config={col1Config}
      col2Config={col2Config}
    />
  );
}
