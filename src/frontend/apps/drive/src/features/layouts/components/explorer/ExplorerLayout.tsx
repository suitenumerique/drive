import { login, useAuth } from "@/features/auth/Auth";
import { ExplorerTree } from "@/features/explorer/components/tree/ExplorerTree";
import { MainLayout } from "@gouvfr-lasuite/ui-kit";
import logo from "@/assets/logo.svg";
import { HeaderRight } from "../header/Header";
import {
  ExplorerProvider,
  NavigationEvent,
  useExplorer,
} from "@/features/explorer/components/ExplorerContext";
import { useRouter } from "next/router";
import { ExplorerRightPanelContent } from "@/features/explorer/components/right-panel/ExplorerRightPanelContent";
import { useQuery, useSuspenseQueries } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";

/**
 * This layout is used for the explorer page.
 * It is used to display the explorer tree and the header.
 */
export const ExplorerLayout = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  const router = useRouter();

  const itemId = router.query.id as string;
  const { data: itemChildren } = useQuery({
    queryKey: ["items", itemId, "children"],
    queryFn: () => getDriver().getChildren(itemId),
  });

  if (!useEnsureAuth()) {
    return null;
  }

  const onNavigate = (e: NavigationEvent) => {
    router.push(`/explorer/items/${e.item.id}`);
  };

  return (
    <ExplorerProvider
      itemId={itemId}
      displayMode="app"
      onNavigate={onNavigate}
      childrenItems={itemChildren}
    >
      <MainExplorerLayout>{children}</MainExplorerLayout>
    </ExplorerProvider>
  );
};

export const useEnsureAuth = () => {
  const { user } = useAuth();

  if (!user) {
    login();
  }

  return !!user;
};

export const MainExplorerLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const {
    rightPanelOpen,
    setRightPanelOpen,
    rightPanelForcedItem: rightPanelItem,
  } = useExplorer();

  return (
    <MainLayout
      enableResize
      rightPanelContent={<ExplorerRightPanelContent item={rightPanelItem} />}
      rightPanelIsOpen={rightPanelOpen}
      onToggleRightPanel={() => setRightPanelOpen(!rightPanelOpen)}
      leftPanelContent={<ExplorerTree />}
      icon={<img src={logo.src} alt="logo" />}
      rightHeaderContent={<HeaderRight />}
    >
      {children}
    </MainLayout>
  );
};
