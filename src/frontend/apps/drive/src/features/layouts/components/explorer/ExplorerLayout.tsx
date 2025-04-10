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
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { useEffect } from "react";
import { GlobalLayout } from "../global/GlobalLayout";

export const getGlobalExplorerLayout = (page: React.ReactElement) => {
  return <GlobalExplorerLayout>{page}</GlobalExplorerLayout>;
};

export const GlobalExplorerLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  // TODO: Handle auth redirect here maybe ?
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
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    console.log("COUCOU PANPAN");

    return () => {
      console.log("BYE BYE PANPAN");
    };
  }, []);

  const itemId = router.query.id as string;
  const onNavigate = (e: NavigationEvent) => {
    router.push(`/explorer/items/${e.item.id}`);
  };

  return (
    <ExplorerProvider itemId={itemId} displayMode="app" onNavigate={onNavigate}>
      <ExplorerPanelsLayout>{children}</ExplorerPanelsLayout>
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

export const ExplorerPanelsLayout = ({
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
