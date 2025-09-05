import { useAuth } from "@/features/auth/Auth";
import { ExplorerTree } from "@/features/explorer/components/tree/ExplorerTree";
import { MainLayout } from "@gouvfr-lasuite/ui-kit";
import { HeaderIcon, HeaderRight } from "../header/Header";
import {
  GlobalExplorerProvider,
  NavigationEvent,
  useGlobalExplorer,
} from "@/features/explorer/components/GlobalExplorerContext";
import { useRouter } from "next/router";
import { ExplorerRightPanelContent } from "@/features/explorer/components/right-panel/ExplorerRightPanelContent";
import { GlobalLayout } from "../global/GlobalLayout";
import { LeftPanelMobile } from "../left-panel/LeftPanelMobile";

export const getGlobalExplorerLayout = (page: React.ReactElement) => {
  return <GlobalExplorerLayout>{page}</GlobalExplorerLayout>;
};

export const GlobalExplorerLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  return (
    <GlobalLayout>
      <ExplorerLayout>{children}</ExplorerLayout>
    </GlobalLayout>
  );
};

/**
 * This layout is used for the explorer page.
 * It is used to display the explorer tree and the header.
 */
export const ExplorerLayout = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();

  const itemId = router.query.id as string;
  const onNavigate = (e: NavigationEvent) => {
    router.push(`/explorer/items/${e.item.id}`);
  };

  return (
    <GlobalExplorerProvider
      itemId={itemId}
      displayMode="app"
      onNavigate={onNavigate}
    >
      <ExplorerPanelsLayout>{children}</ExplorerPanelsLayout>
    </GlobalExplorerProvider>
  );
};

export const ExplorerPanelsLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const {
    rightPanelOpen,
    setRightPanelOpen,
    rightPanelForcedItem: rightPanelItem,
    isLeftPanelOpen,
    setIsLeftPanelOpen,
  } = useGlobalExplorer();

  const { user } = useAuth();

  return (
    <MainLayout
      enableResize
      rightPanelContent={<ExplorerRightPanelContent item={rightPanelItem} />}
      rightPanelIsOpen={rightPanelOpen}
      onToggleRightPanel={() => setRightPanelOpen(!rightPanelOpen)}
      leftPanelContent={user ? <ExplorerTree /> : <LeftPanelMobile />}
      isLeftPanelOpen={isLeftPanelOpen}
      hideLeftPanelOnDesktop={!user}
      setIsLeftPanelOpen={() => setIsLeftPanelOpen(!isLeftPanelOpen)}
      icon={<HeaderIcon />}
      rightHeaderContent={<HeaderRight displaySearch={true} />}
    >
      {children}
    </MainLayout>
  );
};
