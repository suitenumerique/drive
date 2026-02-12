import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import WorkspacesExplorer from "@/features/explorer/components/workspaces-explorer/WorkspacesExplorer";
import { setFromRoute } from "@/features/explorer/utils/utils";
import { DefaultRoute } from "@/utils/defaultRoutes";
import { useEffect } from "react";
export default function SharedPage() {
  useEffect(() => {
    setFromRoute(DefaultRoute.SHARED_WITH_ME);
  }, []);
  return <WorkspacesExplorer defaultFilters={{ is_creator_me: false }} />;
}

SharedPage.getLayout = getGlobalExplorerLayout;
