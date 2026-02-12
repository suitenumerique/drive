import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { ItemFilters } from "@/features/drivers/Driver";
import { useMemo, useState } from "react";
import { useInfiniteRecentItems } from "@/features/explorer/hooks/useInfiniteItems";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { setFromRoute } from "@/features/explorer/utils/utils";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { useEffect } from "react";
export default function RecentPage() {
  const [filters, setFilters] = useState<ItemFilters>({});

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } =
    useInfiniteRecentItems(filters);

  // Flatten all pages into a single array of items
  const itemChildren = useMemo(() => {
    return data?.pages.flatMap((page) => page.children) ?? [];
  }, [data]);

  useEffect(() => {
    setFromRoute(DefaultRoute.RECENT);
  }, []);

  return (
    <AppExplorer
      childrenItems={itemChildren}
      filters={filters}
      onFiltersChange={setFilters}
      hasNextPage={hasNextPage}
      showFilters={true}
      isFetchingNextPage={isFetchingNextPage}
      fetchNextPage={fetchNextPage}
      isLoading={isLoading}
    />
  );
}

RecentPage.getLayout = getGlobalExplorerLayout;
