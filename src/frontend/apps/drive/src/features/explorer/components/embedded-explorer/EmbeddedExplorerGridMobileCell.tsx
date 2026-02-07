import { CellContext } from "@tanstack/react-table";
import { useState } from "react";
import { Item } from "@/features/drivers/types";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { timeAgo } from "@/features/explorer/utils/utils";
import { removeFileExtension } from "../../utils/mimeTypes";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { useEmbeddedExplorerGirdContext } from "./EmbeddedExplorerGrid";

type EmbeddedExplorerGridMobileCellProps = CellContext<Item, unknown>;

export const EmbeddedExplorerGridMobileCell = (
  params: EmbeddedExplorerGridMobileCellProps
) => {
  const item = params.row.original;
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const { setIsActionModalOpen } = useEmbeddedExplorerGirdContext();

  const handleModalOpenChange = (value: boolean) => {
    setIsActionModalOpen(value);
  };

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
      <div
        className="explorer__grid__item__mobile__actions"
        role="presentation"
        onClick={(e) => {
          e.stopPropagation();
        }}
        onKeyDown={(e) => {
          e.stopPropagation();
        }}
      >
        <ItemActionDropdown
          item={item}
          isOpen={isOpen}
          setIsOpen={setIsOpen}
          onModalOpenChange={handleModalOpenChange}
          trigger={
            <Button
              variant="tertiary"
              size="small"
              onClick={() => setIsOpen(!isOpen)}
              aria-label={t("explorer.grid.actions.button_aria_label", {
                name: item.title,
              })}
              icon={<span className="material-icons">more_vert</span>}
            />
          }
        />
      </div>
    </div>
  );
};
