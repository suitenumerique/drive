import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { useInfiniteChildren } from "@/features/explorer/hooks/useInfiniteChildren";
import { useRouter } from "next/router";
import { useState, useMemo } from "react";
export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;
  const [filters, setFilters] = useState<ItemFilters>({});

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } =
    useInfiniteChildren(itemId, filters);

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

ItemPage.getLayout = getGlobalExplorerLayout;
