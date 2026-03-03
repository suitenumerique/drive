import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { ItemFilters } from "@/features/drivers/Driver";
import { useMemo, useState } from "react";
import { useInfiniteRecentItems } from "@/features/explorer/hooks/useInfiniteItems";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { useDefaultRoute } from "@/hooks/useDefaultRoute";
import { ItemType } from "@/features/drivers/types";
import { useGridColumns } from "@/features/explorer/hooks/useGridColumns";
import { computeFilters } from "@/features/explorer/utils/ordering";

export default function RecentPage() {
  const [filters, setFilters] = useState<ItemFilters>({
    type: ItemType.FILE,
  });

  const {
    col1Config,
    col2Config,
    sortState,
    cycleSortForColumn,
    setColumn,
    prefs,
    viewConfig,
  } = useGridColumns(DefaultRoute.RECENT);

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
  } = useInfiniteRecentItems(finalFilters);

  // Flatten all pages into a single array of items
  const itemChildren = useMemo(() => {
    return data?.pages.flatMap((page) => page.children) ?? [];
  }, [data]);

  useDefaultRoute(DefaultRoute.RECENT);

  return (
    <AppExplorer
      childrenItems={itemChildren}
      filters={filters}
      onFiltersChange={setFilters}
      hasNextPage={hasNextPage}
      showFilters={true}
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

RecentPage.getLayout = getGlobalExplorerLayout;
