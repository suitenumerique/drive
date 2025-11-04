import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { timeAgo } from "@/features/explorer/utils/utils";
import { removeFileExtension } from "../../utils/mimeTypes";
type EmbeddedExplorerGridMobileCellProps = CellContext<Item, unknown>;

export const EmbeddedExplorerGridMobileCell = (
  params: EmbeddedExplorerGridMobileCellProps
) => {
  const item = params.row.original;

  return (
    <div className="explorer__grid__item__mobile">
      <ItemIcon key={item.id} item={item} />
      <div className="explorer__grid__item__mobile__info">
        <div className="explorer__grid__item__mobile__info__title">
          <span className="explorer__grid__item__name__text">
            {removeFileExtension(item.title)}
          </span>
        </div>
        <div className="explorer__grid__item__mobile__info__meta">
          <span>{timeAgo(new Date(item.updated_at))}</span>
        </div>
      </div>
    </div>
  );
};
