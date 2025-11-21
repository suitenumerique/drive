import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { useState, useMemo } from "react";
import { useInfiniteItems } from "@/features/explorer/hooks/useInfiniteItems";
import { WorkspaceType } from "@/features/drivers/types";
export default function SharedPage() {
  const [filters, setFilters] = useState<ItemFilters>({
    workspaces: WorkspaceType.SHARED,
  });

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

SharedPage.getLayout = getGlobalExplorerLayout;
