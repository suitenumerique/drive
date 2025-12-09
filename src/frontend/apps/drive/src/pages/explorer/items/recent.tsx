import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
export default function RecentPage() {
  return <WorkspacesExplorer defaultFilters={{}} />;
}

RecentPage.getLayout = getGlobalExplorerLayout;
