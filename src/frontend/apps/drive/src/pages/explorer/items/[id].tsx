import { getDriver } from "@/features/config/Config";
import { Explorer } from "@/features/explorer/components/Explorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/router";

export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;
  const { data: itemChildren } = useQuery({
    queryKey: ["items", itemId, "children"],
    queryFn: () => getDriver().getChildren(itemId),
  });

  return <Explorer childrenItems={itemChildren} />;
}

ItemPage.getLayout = getGlobalExplorerLayout;
