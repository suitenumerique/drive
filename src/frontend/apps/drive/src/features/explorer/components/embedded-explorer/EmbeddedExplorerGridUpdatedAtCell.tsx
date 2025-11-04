import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { Tooltip } from "@openfun/cunningham-react";
import { timeAgo } from "@/features/explorer/utils/utils";
import { Draggable } from "@/features/explorer/components/Draggable";
import { useDisableDragGridItem } from "@/features/explorer/components/embedded-explorer/hooks";

type EmbeddedExplorerGridUpdatedAtCellProps = CellContext<Item, Date>;

export const EmbeddedExplorerGridUpdatedAtCell = (
  params: EmbeddedExplorerGridUpdatedAtCellProps
) => {
  const item = params.row.original;
  const disableDrag = useDisableDragGridItem(item);

  return (
    <Draggable id={params.cell.id} item={item} disabled={disableDrag}>
      <div className="explorer__grid__item__last-update">
        <Tooltip content={params.row.original.updated_at.toLocaleString()}>
          <span>{timeAgo(new Date(item.updated_at))}</span>
        </Tooltip>
      </div>
    </Draggable>
  );
};
