import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";
import { Explorer } from "@/features/explorer/components/Explorer";
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
    <Explorer
      childrenItems={itemChildren}
      filters={filters}
      onFiltersChange={setFilters}
    />
  );
}

ItemPage.getLayout = getGlobalExplorerLayout;
