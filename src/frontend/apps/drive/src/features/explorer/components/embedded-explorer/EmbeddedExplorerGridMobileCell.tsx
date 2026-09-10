import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { memo } from "react";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { timeAgo } from "@/features/explorer/utils/utils";
import { LoadingRing } from "@/features/ui/components/loading-ring/LoadingRing";
import { useTransientItem } from "@/features/explorer/hooks/useTransientItem";
import clsx from "clsx";
import { removeFileExtension } from "@gouvfr-lasuite/ui-components";

type EmbeddedExplorerGridMobileCellProps = CellContext<Item, unknown>;

const EmbeddedExplorerGridMobileCellComponent = (
  params: EmbeddedExplorerGridMobileCellProps,
) => {
  const item = params.row.original;
  const { isTransient, label: transientLabel } = useTransientItem(item);

  return (
    <div className="explorer__grid__item__mobile">
      {isTransient ? (
        <div className="explorer__grid__item__name__spinner-container">
          <LoadingRing size="md" />
        </div>
      ) : (
        <ItemIcon key={item.id} item={item} />
      )}
      <div className="explorer__grid__item__mobile__info">
        <div className="explorer__grid__item__mobile__info__title">
          <span
            className={clsx("explorer__grid__item__name__text", {
              "explorer__grid__item__name--duplicating-text": isTransient,
            })}
          >
            {removeFileExtension(item.title)}
            {isTransient && (
              <span className="explorer__grid__item__name__duplicating-label">
                {" "}
                ({transientLabel})
              </span>
            )}
          </span>
        </div>
        <div className="explorer__grid__item__mobile__info__meta">
          <span>{timeAgo(new Date(item.updated_at))}</span>
        </div>
      </div>
    </div>
  );
};

export const EmbeddedExplorerGridMobileCell = memo(
  EmbeddedExplorerGridMobileCellComponent,
);
