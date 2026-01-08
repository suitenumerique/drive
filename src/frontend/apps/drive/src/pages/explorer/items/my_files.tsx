import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";

export default function MyFilesPage() {
  return <WorkspacesExplorer defaultFilters={{ is_creator_me: true }} />;
}

MyFilesPage.getLayout = getGlobalExplorerLayout;
