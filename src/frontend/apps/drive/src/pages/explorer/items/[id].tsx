import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { useInfiniteChildren } from "@/features/explorer/hooks/useInfiniteChildren";
import { useItem } from "@/features/explorer/hooks/useQueries";
import { isLink } from "@/features/drivers/utils";
import { useRouter } from "next/router";
import { useState, useMemo, useEffect } from "react";

export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;
  const [filters, setFilters] = useState<ItemFilters>({});

  // Shared item URLs all land here: a link has nothing to explore, go to its URL.
  const { data: item } = useItem(itemId, { enabled: !!itemId });
  const linkUrl =
    item?.id === itemId && isLink(item) ? (item.link_url ?? null) : null;
  useEffect(() => {
    if (linkUrl) {
      window.location.replace(linkUrl);
    }
  }, [linkUrl]);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isPlaceholderData,
  } = useInfiniteChildren(itemId, filters);

  // Flatten all pages into a single array of items
  const itemChildren = useMemo(() => {
    return data?.pages.flatMap((page) => page.children) ?? [];
  }, [data]);

  if (linkUrl) {
    return null;
  }

  return (
    <AppExplorer
      viewConfigKey="folder"
      navigationId={itemId}
      onComputedFiltersChange={setFilters}
      childrenItems={itemChildren}
      hasNextPage={hasNextPage}
      isFetchingNextPage={isFetchingNextPage}
      fetchNextPage={fetchNextPage}
      isLoading={isLoading || isPlaceholderData}
    />
  );
}

ItemPage.getLayout = getGlobalExplorerLayout;
