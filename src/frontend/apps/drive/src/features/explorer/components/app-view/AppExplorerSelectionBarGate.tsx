import { HorizontalSeparator } from "@gouvfr-lasuite/ui-kit";
import { useHasSelection } from "@/features/explorer/stores/selectionStore";
import { ExplorerSelectionBar } from "@/features/explorer/components/app-view/ExplorerSelectionBar";
import { ExplorerFilters } from "@/features/explorer/components/app-view/ExplorerFilters";

/**
 * Isolates the selection-driven subscription so that the flip
 * hasSelection false↔true only re-renders this small component — not
 * AppExplorerInner and its whole subtree (which would cascade into the
 * grid and cause a hitch on the 0→n and n→0 transitions of a marquee
 * selection).
 */
export const AppExplorerSelectionBarGate = ({
  showFilters,
}: {
  showFilters: boolean;
}) => {
  const hasSelection = useHasSelection();

  if (hasSelection) {
    return <ExplorerSelectionBar />;
  }
  if (showFilters) {
    return <ExplorerFilters />;
  }
  return <HorizontalSeparator withPadding={false} />;
};
