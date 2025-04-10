import { getDriver } from "@/features/config/Config";
import { Explorer } from "@/features/explorer/components/Explorer";
import { ExplorerProvider } from "@/features/explorer/components/ExplorerContext";
import { NavigationEvent } from "@/features/explorer/components/ExplorerContext";
import {
  getGlobalExplorerLayout,
  MainExplorerLayout,
} from "@/features/layouts/components/explorer/ExplorerLayout";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/router";

// TODO:
// OK: Obligé de garder: TrashPage.getLayout = ItemPage.getLayout; pour avoir un contexte global + arbre maintenu entre les navs
// On retire TOUTE logique d'enfant du ExplorerContext
// la custom est uniquement dans TrashPage
// les selectedItems sont remontés du ExplorerInner à ExplorerContext en tant qu'entités du coup
// l'authent user doit redirect au login si pas de user
// disable dnd on some views
// le useEffect }, [rightPanelForcedItem]);

export default function TrashPage() {
  const { data: trashItems } = useQuery({
    queryKey: ["items", "trash"],
    queryFn: () => getDriver().getTrashItems(),
  });

  return <Explorer items={trashItems} />;
}

TrashPage.getLayout = getGlobalExplorerLayout;

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
