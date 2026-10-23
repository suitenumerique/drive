import { useGlobalExplorer } from "../GlobalExplorerContext";
import { useTreeUtils } from "../../hooks/useTreeUtils";

export function useAppRestrictionUpdated() {
  const { setRightPanelForcedItem } = useGlobalExplorer();
  const { refreshFavorites } = useTreeUtils();

  return async () => {
    // Restriction changes can leave the right panel showing an outdated item.
    // Refresh the Favorites tree too: its data lives outside the query cache.
    setRightPanelForcedItem(undefined);
    await refreshFavorites();
  };
}
