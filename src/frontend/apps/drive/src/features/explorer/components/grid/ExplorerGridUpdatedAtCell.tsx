import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { Tooltip } from "@openfun/cunningham-react";
import { timeAgo } from "../../utils/utils";
import { Draggable } from "../Draggable";
import { useDisableDragGridItem } from "./hooks";

type ExplorerGridUpdatedAtCellProps = CellContext<Item, Date>;

export const ExplorerGridUpdatedAtCell = (
  params: ExplorerGridUpdatedAtCellProps
) => {
  const item = params.row.original;
  const disableDrag = useDisableDragGridItem(item);

  return (
    <Draggable id={params.cell.id} item={item} disabled={disableDrag}>
      <div className="explorer__grid__item__last-update">
        <Tooltip content={params.row.original.updated_at.toLocaleString()}>
          <span>{timeAgo(params.row.original.updated_at)}</span>
        </Tooltip>
      </div>
    </Draggable>
  );
};
