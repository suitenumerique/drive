import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { isFolder } from "@/features/drivers/utils";
import { Draggable } from "@/features/explorer/components/Draggable";
import { useDisableDragGridItem } from "@/features/explorer/components/embedded-explorer/hooks";
import { useTranslation } from "react-i18next";
import { getExtension } from "@/features/explorer/utils/utils";

export const FileTypeCell = (params: CellContext<Item, unknown>) => {
  const { t } = useTranslation();
  const item = params.row.original;
  const disableDrag = useDisableDragGridItem(item);

  const extension = isFolder(item) ? null : getExtension(item);
  const label = isFolder(item)
    ? t("explorer.grid.columns.folder")
    : extension
      ? `.${extension}`
      : "-";

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
