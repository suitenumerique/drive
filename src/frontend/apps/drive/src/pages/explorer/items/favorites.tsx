import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
import { setFromRoute } from "@/features/explorer/utils/utils";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { useEffect } from "react";

export default function FavoritesPage() {
  useEffect(() => {
    setFromRoute(DefaultRoute.FAVORITES);
  }, []);
  return <WorkspacesExplorer defaultFilters={{ is_favorite: true }} />;
}

FavoritesPage.getLayout = getGlobalExplorerLayout;
