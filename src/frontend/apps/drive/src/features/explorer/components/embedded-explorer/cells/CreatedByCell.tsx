import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { Draggable } from "@/features/explorer/components/Draggable";
import { useDisableDragGridItem } from "@/features/explorer/components/embedded-explorer/hooks";

export const CreatedByCell = (params: CellContext<Item, unknown>) => {
  const item = params.row.original;
  const disableDrag = useDisableDragGridItem(item);
  const displayName = item.creator?.full_name || item.creator?.short_name || "";

  return (
    <Draggable id={params.cell.id} item={item} disabled={disableDrag}>
      <div className="explorer__grid__item__cell-value">
        <span>{displayName}</span>
      </div>
    </Draggable>
  );
};
