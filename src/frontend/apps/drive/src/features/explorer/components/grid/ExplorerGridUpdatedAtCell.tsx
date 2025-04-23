import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { Tooltip } from "@openfun/cunningham-react";
import { timeAgo } from "../../utils/utils";
import { useExplorer } from "../ExplorerContext";
import { useExplorerInner } from "../Explorer";
import { Draggable } from "../Draggable";

type ExplorerGridUpdatedAtCellProps = CellContext<Item, Date>;

export const ExplorerGridUpdatedAtCell = (
  params: ExplorerGridUpdatedAtCellProps
) => {
  const item = params.row.original;
  const { selectedItemsMap } = useExplorer();
  const { disableItemDragAndDrop } = useExplorerInner();
  const isSelected = !!selectedItemsMap[item.id];

  return (
    <Draggable
      id={params.cell.id}
      item={item}
      disabled={disableItemDragAndDrop || !isSelected}
    >
      <div className="explorer__grid__item__last-update">
        <Tooltip content={params.row.original.updated_at.toLocaleString()}>
          <span>{timeAgo(params.row.original.updated_at)}</span>
        </Tooltip>
      </div>
    </Draggable>
  );
};
