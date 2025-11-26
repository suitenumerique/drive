import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { WorkspaceType } from "@/features/drivers/types";
import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
export default function SharedPage() {
  return (
    <WorkspacesExplorer
      defaultFilters={{ workspaces: WorkspaceType.SHARED }}
      showFilters={false}
    />
  );
}

SharedPage.getLayout = getGlobalExplorerLayout;
