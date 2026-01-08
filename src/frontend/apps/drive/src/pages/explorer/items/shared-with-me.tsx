import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
export default function SharedPage() {
  return <WorkspacesExplorer defaultFilters={{ is_creator_me: false }} />;
}

SharedPage.getLayout = getGlobalExplorerLayout;
