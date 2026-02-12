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
import { useSyncUserLanguage } from "../../hooks/useSyncUserLanguage";
import { Item } from "@/features/drivers/types";
import { ReleaseNoteAuto } from "@/features/ui/components/release-note";
import { setManualNavigationItemId } from "@/features/explorer/utils/utils";

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
      <ReleaseNoteAuto />
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
    // Only keep "minimal" in the query string so that when navigating, to keep the minimal layout on the next page
    // the minimal layout state is preserved; all other query params are dropped intentionally.
    const { minimal } = router.query;
    const item = e.item as Item;
    const query = minimal ? { minimal } : {};
    // If the itemId is a favorite item, we need to get the favorite items. cf onLoadChildren in GlobalExplorerProvider.tsx
    const id = item.originalId ?? item.id;
    setManualNavigationItemId(id);
    router.push({ pathname: `/explorer/items/${id}`, query });
  };

  useSyncUserLanguage();

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
