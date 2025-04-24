import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { useEffect, useRef, useState } from "react";
import { Draggable } from "../Draggable";
import { Tooltip } from "@openfun/cunningham-react";
import { useExplorer } from "../ExplorerContext";
import { ItemIcon } from "../ItemIcon";
import { useExplorerInner } from "../Explorer";
import { useDisableDragGridItem } from "./hooks";
type ExplorerGridNameCellProps = CellContext<Item, string>;

export const ExplorerGridNameCell = (params: ExplorerGridNameCellProps) => {
  const item = params.row.original;
  const ref = useRef<HTMLSpanElement>(null);
  const [isOverflown, setIsOverflown] = useState(false);
  const { selectedItemsMap } = useExplorer();
  const { disableItemDragAndDrop } = useExplorerInner();
  const isSelected = !!selectedItemsMap[item.id];
  const canMove = item.abilities.move;
  const disableDrag = useDisableDragGridItem(item);

  const renderTitle = () => {
    // We need to have the element holding the ref nested because the Tooltip component
    // seems to make the top-most children ref null.
    return (
      <Draggable
        id={params.cell.id + "-title"}
        item={item}
        style={{ display: "flex", overflow: "hidden" }}
        disabled={disableItemDragAndDrop || isSelected || !canMove} // If it's selected then we can drag on the entire cell
      >
        <div style={{ display: "flex", overflow: "hidden" }}>
          <span className="explorer__grid__item__name__text" ref={ref}>
            {item.title}
          </span>
        </div>
      </Draggable>
    );
  };

  useEffect(() => {
    const checkOverflow = () => {
      const element = ref.current;
      // Should always be defined, but just in case.
      if (element) {
        setIsOverflown(element.scrollWidth > element.clientWidth);
      }
    };
    checkOverflow();

    window.addEventListener("resize", checkOverflow);
    return () => {
      window.removeEventListener("resize", checkOverflow);
    };
  }, [item.title]);

  return (
    <Draggable id={params.cell.id} item={item} disabled={disableDrag}>
      <div className="explorer__grid__item__name">
        <ItemIcon key={item.id} item={item} />
        {isOverflown ? (
          <Tooltip content={item.title}>{renderTitle()}</Tooltip>
        ) : (
          renderTitle()
        )}
      </div>
    </Draggable>
  );
};
