import SelectionArea, { SelectionEvent } from "@viselect/react";
import { database } from "./database";
import { ExplorerGrid } from "./ExplorerGrid";
import { ExplorerBreadcrumbs } from "./ExplorerBreadcrumbs";
import { useExplorer } from "./Explorer";
import { ExplorerSelectionBar } from "./ExplorerSelectionBar";

export const ExplorerInner = () => {
  const {
    selectedItems,
    setSelectedItems,
    displayMode,
    selectedItemsEntities,
  } = useExplorer();

  const onSelectionStart = ({ event, selection }: SelectionEvent) => {
    if (!event?.ctrlKey && !event?.metaKey) {
      selection.clearSelection();
      setSelectedItems({});
    }
  };

  const onSelectionMove = ({
    store: {
      changed: { added, removed },
    },
  }: SelectionEvent) => {
    setSelectedItems((prev) => {
      const next = { ...prev };
      added.forEach((element) => {
        const id = element.getAttribute("data-id");
        if (id) next[id] = true;
      });
      removed.forEach((element) => {
        const id = element.getAttribute("data-id");
        if (id) delete next[id];
      });
      return next;
    });
  };

  return (
    <SelectionArea
      onStart={onSelectionStart}
      onMove={onSelectionMove}
      selectables=".selectable"
      className="selection-area__container"
      features={{
        range: true,
        touch: true,
        singleTap: {
          // We do not want to allow singleTap to select items, otherwise it overrides the onClick event of the TR
          // element, and also blocks the click on the action dropdown menu. We rather implement it by ourselves.
          allow: false,
          intersect: "native",
        },
      }}
    >
      <div className={`explorer explorer--${displayMode}`}>
        <div className="explorer__container">
          {selectedItemsEntities.length > 0 ? (
            <ExplorerSelectionBar />
          ) : (
            <div className="explorer__filters">Filters</div>
          )}

          <div className="explorer__content">
            <ExplorerBreadcrumbs />
            <ExplorerGrid />
          </div>
        </div>
      </div>
    </SelectionArea>
  );
};
