import { CellContext } from "@tanstack/react-table";
import { Item, ItemType } from "@/features/drivers/types";
import { Draggable } from "@/features/explorer/components/Draggable";
import { useDisableDragGridItem } from "@/features/explorer/components/embedded-explorer/hooks";
import { formatSize } from "@/features/explorer/utils/utils";
import { useTranslation } from "react-i18next";

export const FileSizeCell = (params: CellContext<Item, unknown>) => {
  const { t } = useTranslation();
  const item = params.row.original;
  const disableDrag = useDisableDragGridItem(item);

  const label =
    item.type === ItemType.FOLDER || !item.size ? "-" : formatSize(item.size, t);

  return (
    <Draggable id={params.cell.id} item={item} disabled={disableDrag}>
      <div className="explorer__grid__item__cell-value">
        <span>{label}</span>
      </div>
    </Draggable>
  );
};
