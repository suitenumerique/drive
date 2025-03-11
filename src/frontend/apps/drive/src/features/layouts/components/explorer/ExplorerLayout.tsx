import { login, useAuth } from "@/features/auth/Auth";
import { ExplorerTree } from "@/features/explorer/components/ExplorerTree";
import { MainLayout } from "@lasuite/ui-kit";
import logo from "@/assets/logo.svg";
import { HeaderRight } from "../header/Header";
import {
  ExplorerProvider,
  NavigationEvent,
} from "@/features/explorer/components/ExplorerContext";
import { useRouter } from "next/router";

/**
 * This layout is used for the explorer page.
 * It is used to display the explorer tree and the header.
 */
export const ExplorerLayout = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  const router = useRouter();

  if (!user) {
    login();
    return null;
  }

  const onNavigate = (e: NavigationEvent) => {
    router.push(`/explorer/items/${e.item.id}`);
  };

  return (
    <ExplorerProvider
      itemId={router.query.id as string}
      displayMode="app"
      onNavigate={onNavigate}
    >
      <MainLayout
        enableResize
        leftPanelContent={<ExplorerTree />}
        icon={<img src={logo.src} alt="logo" />}
        rightHeaderContent={<HeaderRight />}
      >
        {children}
      </MainLayout>
    </ExplorerProvider>
  );
};
