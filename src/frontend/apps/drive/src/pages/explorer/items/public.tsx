import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { WorkspaceType } from "@/features/drivers/types";
import DefaultAppViewWithFilter from "@/features/explorer/components/app-view/DefaultAppViewWithFilter";
export default function PublicPage() {
  return (
    <DefaultAppViewWithFilter
      defaultFilters={{ workspaces: WorkspaceType.PUBLIC }}
    />
  );
}

PublicPage.getLayout = getGlobalExplorerLayout;
