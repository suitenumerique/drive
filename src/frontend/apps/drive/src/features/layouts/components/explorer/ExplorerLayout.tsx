import { login, useAuth } from "@/features/auth/Auth";
import { ExplorerTree } from "@/features/explorer/components/tree/ExplorerTree";
import { MainLayout } from "@gouvfr-lasuite/ui-kit";
import logo from "@/assets/logo_alpha.svg";
import { HeaderRight } from "../header/Header";
import {
  GlobalExplorerProvider,
  NavigationEvent,
  useGlobalExplorer,
} from "@/features/explorer/components/GlobalExplorerContext";
import { useRouter } from "next/router";
import { ExplorerRightPanelContent } from "@/features/explorer/components/right-panel/ExplorerRightPanelContent";
import { GlobalLayout } from "../global/GlobalLayout";
import { useEffect } from "react";
import { Feedback } from "@/features/feedback/Feedback";

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
      <AuthLayout>
        <ExplorerLayout>{children}</ExplorerLayout>
      </AuthLayout>
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

export const AuthLayout = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();

  useEffect(() => {
    if (user === null) {
      login();
    }
  }, [user]);

  if (!user) {
    return null;
  }

  return children;
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

  return (
    <MainLayout
      enableResize
      rightPanelContent={<ExplorerRightPanelContent item={rightPanelItem} />}
      rightPanelIsOpen={rightPanelOpen}
      onToggleRightPanel={() => setRightPanelOpen(!rightPanelOpen)}
      leftPanelContent={<ExplorerTree />}
      isLeftPanelOpen={isLeftPanelOpen}
      setIsLeftPanelOpen={() => setIsLeftPanelOpen(!isLeftPanelOpen)}
      icon={
        <div className="drive__header__left">
          <img src={logo.src} alt="logo" />
          <Feedback />
        </div>
      }
      rightHeaderContent={<HeaderRight />}
    >
      {children}
    </MainLayout>
  );
};
