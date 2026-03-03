import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { useInfiniteChildren } from "@/features/explorer/hooks/useInfiniteChildren";
import { useRouter } from "next/router";
import { useState, useMemo } from "react";
import { useGridColumns } from "@/features/explorer/hooks/useGridColumns";
import { computeFilters } from "@/features/explorer/utils/ordering";

export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;
  const [filters, setFilters] = useState<ItemFilters>({});

  const {
    col1Config,
    col2Config,
    sortState,
    cycleSortForColumn,
    setColumn,
    prefs,
    viewConfig,
  } = useGridColumns("folder", itemId);

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
  } = useInfiniteChildren(itemId, finalFilters);

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

ItemPage.getLayout = getGlobalExplorerLayout;
