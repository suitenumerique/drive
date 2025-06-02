import { Explorer } from "@/features/explorer/components/Explorer";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useRouter } from "next/router";
import {
  ExplorerProvider,
  NavigationEvent,
  useExplorer,
} from "@/features/explorer/components/ExplorerContext";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ItemFilters } from "@/features/drivers/Driver";
import { getDriver } from "@/features/config/Config";
import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

/**
 * This route is gonna be used later for SKD integration as iframe.
 */
export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;
  const [filters, setFilters] = useState<ItemFilters>({});
  const { t } = useTranslation();

  const onNavigate = (e: NavigationEvent) => {
    router.push(`/sdk/explorer/items/${e.item.id}`);
  };

  const { data: children } = useQuery({
    queryKey: [
      "items",
      itemId,
      "children",
      ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
    ],
    queryFn: () => getDriver().getChildren(itemId, filters),
  });

  return (
    <ExplorerProvider itemId={itemId} displayMode="sdk" onNavigate={onNavigate}>
      <Explorer
        childrenItems={children}
        filters={filters}
        onFiltersChange={setFilters}
      />
      <Footer />
    </ExplorerProvider>
  );
}

ItemPage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};
const Footer = () => {
  const { t } = useTranslation();

  const { selectedItems } = useExplorer();

  const onChoose = () => {
    window.opener.postMessage(
      {
        type: "items-selected",
        data: {
          items: selectedItems,
        },
      },
      "*"
    );
  };

  return (
    <div className="explorer__footer">
      <Button onClick={onChoose}>{t("sdk.explorer.choose")}</Button>
    </div>
  );
};
