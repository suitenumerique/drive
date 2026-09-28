import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { ItemFilters } from "@/features/drivers/Driver";
import { useMemo, useState } from "react";
import { useInfiniteRecentItems } from "@/features/explorer/hooks/useInfiniteItems";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { useDefaultRoute } from "@/hooks/useDefaultRoute";

export default function RecentPage() {
  const [filters, setFilters] = useState<ItemFilters>({});

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isPlaceholderData,
  } = useInfiniteRecentItems(filters);

  // Flatten all pages into a single array of items
  const itemChildren = useMemo(() => {
    return data?.pages.flatMap((page) => page.children) ?? [];
  }, [data]);

  useDefaultRoute(DefaultRoute.RECENT);

  return (
    <AppExplorer
      viewConfigKey={DefaultRoute.RECENT}
      onComputedFiltersChange={setFilters}
      childrenItems={itemChildren}
      hasNextPage={hasNextPage}
      showFilters={true}
      isFetchingNextPage={isFetchingNextPage}
      fetchNextPage={fetchNextPage}
      isLoading={isLoading || isPlaceholderData}
    />
  );
}

RecentPage.getLayout = getGlobalExplorerLayout;
