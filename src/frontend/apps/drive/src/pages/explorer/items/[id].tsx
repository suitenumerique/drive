import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/router";
import { useState } from "react";

export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;
  const [filters, setFilters] = useState<ItemFilters>({});
  const { data: itemChildren } = useQuery({
    queryKey: [
      "items",
      itemId,
      "children",
      ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
    ],
    queryFn: () => getDriver().getChildren(itemId, filters),
  });

  return (
    <AppExplorer
      childrenItems={itemChildren}
      filters={filters}
      onFiltersChange={setFilters}
    />
  );
}

ItemPage.getLayout = getGlobalExplorerLayout;
