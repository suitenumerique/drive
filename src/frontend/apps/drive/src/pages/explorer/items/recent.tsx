import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
import { ItemFiltersOrdering } from "@/features/drivers/Driver";
export default function RecentPage() {
  return (
    <WorkspacesExplorer
      defaultFilters={{ ordering: ItemFiltersOrdering.UPDATED_AT_DESC }}
    />
  );
}

RecentPage.getLayout = getGlobalExplorerLayout;
