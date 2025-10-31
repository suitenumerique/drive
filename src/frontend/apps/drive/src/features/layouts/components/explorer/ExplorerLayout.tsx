/* eslint-disable @typescript-eslint/no-unused-vars */
import { useAuth } from "@/features/auth/Auth";
import { ExplorerTree } from "@/features/explorer/components/tree/ExplorerTree";
import { MainLayout } from "@gouvfr-lasuite/ui-kit";
import { HeaderIcon, HeaderRight } from "../header/Header";
import {
  GlobalExplorerProvider,
  NavigationEvent,
  useGlobalExplorer,
} from "@/features/explorer/components/GlobalExplorerContext";
import { ExplorerRightPanelContent } from "@/features/explorer/components/right-panel/ExplorerRightPanelContent";
import { GlobalLayout } from "../global/GlobalLayout";
import { LeftPanelMobile } from "../left-panel/LeftPanelMobile";
import { useRouter } from "next/router";

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
export const ExplorerLayout = ({
  children,
}: {
  children: React.ReactNode;
  isMinimalLayout?: boolean;
}) => {
  const router = useRouter();

  const isMinimalLayout = router.query.minimal === "true";
  const itemId = router.query.id as string;
  const onNavigate = (e: NavigationEvent) => {
    const { id: _id = undefined, ...query } = { ...router.query };

    router.push({ pathname: `/explorer/items/${e.item.id}`, query });
  };

  return (
    <GlobalExplorerProvider
      itemId={itemId}
      displayMode="app"
      onNavigate={onNavigate}
    >
      <ExplorerPanelsLayout isMinimalLayout={isMinimalLayout}>
        {children}
      </ExplorerPanelsLayout>
    </GlobalExplorerProvider>
  );
};

export const ExplorerPanelsLayout = ({
  children,
  isMinimalLayout,
}: {
  children: React.ReactNode;
  isMinimalLayout?: boolean;
}) => {
  const {
    rightPanelOpen,
    setRightPanelOpen,
    item,
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
      hideLeftPanelOnDesktop={!user || isMinimalLayout}
      setIsLeftPanelOpen={() => setIsLeftPanelOpen(!isLeftPanelOpen)}
      icon={<HeaderIcon />}
      rightHeaderContent={
        <HeaderRight displaySearch={isMinimalLayout} currentItem={item} />
      }
    >
      {children}
    </MainLayout>
  );
};
