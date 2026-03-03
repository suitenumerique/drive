import { CellContext } from "@tanstack/react-table";
import { Item, ItemType } from "@/features/drivers/types";
import { Draggable } from "@/features/explorer/components/Draggable";
import { useDisableDragGridItem } from "@/features/explorer/components/embedded-explorer/hooks";
import { useTranslation } from "react-i18next";
import { getFormatTranslationKey } from "@/features/explorer/utils/mimeTypes";

export const FileTypeCell = (params: CellContext<Item, unknown>) => {
  const { t } = useTranslation();
  const item = params.row.original;
  const disableDrag = useDisableDragGridItem(item);

  const label =
    item.type === ItemType.FOLDER
      ? t("explorer.grid.columns.folder")
      : t(getFormatTranslationKey(item));

  return (
    <Draggable id={params.cell.id} item={item} disabled={disableDrag}>
      <div className="explorer__grid__item__cell-value">
        <span>
          {label}
        </span>
      </div>
    </Draggable>
  );
};
