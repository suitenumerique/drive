import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";

export default function FavoritesPage() {
  return <WorkspacesExplorer defaultFilters={{ is_favorite: true }} />;
}

FavoritesPage.getLayout = getGlobalExplorerLayout;
