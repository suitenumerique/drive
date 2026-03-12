import { CellContext } from "@tanstack/react-table";
import { Item, ItemUploadState } from "@/features/drivers/types";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { timeAgo } from "@/features/explorer/utils/utils";
import { removeFileExtension } from "../../utils/mimeTypes";
import { Spinner } from "@/features/ui/components/spinner/Spinner";
import { useTranslation } from "react-i18next";
import { useDuplicatingItemPoll } from "../../hooks/useDuplicatingItemPoll";
import clsx from "clsx";

type EmbeddedExplorerGridMobileCellProps = CellContext<Item, unknown>;

export const EmbeddedExplorerGridMobileCell = (
  params: EmbeddedExplorerGridMobileCellProps,
) => {
  const item = params.row.original;
  const { t } = useTranslation();
  const isDuplicating = item.upload_state === ItemUploadState.DUPLICATING;
  useDuplicatingItemPoll(item);

  return (
    <div className="explorer__grid__item__mobile">
      {isDuplicating ? (
        <div className="explorer__grid__item__name__spinner-container">
          <Spinner size="md" />
        </div>
      ) : (
        <ItemIcon key={item.id} item={item} />
      )}
      <div className="explorer__grid__item__mobile__info">
        <div className="explorer__grid__item__mobile__info__title">
          <span
            className={clsx("explorer__grid__item__name__text", {
              "explorer__grid__item__name--duplicating-text": isDuplicating,
            })}
          >
            {removeFileExtension(item.title)}
            {isDuplicating && (
              <span className="explorer__grid__item__name__duplicating-label">
                {" "}
                ({t("explorer.item.duplicating")})
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
