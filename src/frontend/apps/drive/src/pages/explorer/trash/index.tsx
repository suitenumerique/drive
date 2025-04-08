import { getDriver } from "@/features/config/Config";
import { Explorer } from "@/features/explorer/components/Explorer";
import { ExplorerProvider } from "@/features/explorer/components/ExplorerContext";
import { NavigationEvent } from "@/features/explorer/components/ExplorerContext";
import {
  ExplorerLayout,
  MainExplorerLayout,
  useEnsureAuth,
} from "@/features/layouts/components/explorer/ExplorerLayout";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/router";

export default function TrashPage() {
  if (!useEnsureAuth()) {
    return null;
  }
  return <Explorer />;
}

TrashPage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <ExplorerTrashLayout>{page}</ExplorerTrashLayout>
    </GlobalLayout>
  );
};

/**
 * This layout is used for the explorer page.
 * It is used to display the explorer tree and the header.
 */
export const ExplorerTrashLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const router = useRouter();

  const onNavigate = (e: NavigationEvent) => {
    router.push(`/explorer/items/${e.item.id}`);
  };

  const { data: trashItems } = useQuery({
    queryKey: ["items", "trash"],
    queryFn: () => getDriver().getTrashItems(),
  });

  console.log("trashItems", trashItems);

  return (
    <ExplorerProvider
      itemId={router.query.id as string}
      displayMode="app"
      onNavigate={onNavigate}
      childrenItems={trashItems}
    >
      <MainExplorerLayout>{children}</MainExplorerLayout>
    </ExplorerProvider>
  );
};
