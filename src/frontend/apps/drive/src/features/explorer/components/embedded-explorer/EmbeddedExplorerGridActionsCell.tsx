import { CellContext } from "@tanstack/react-table";
import { Item, ItemUploadState } from "@/features/drivers/types";
import { useState } from "react";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Draggable } from "@/features/explorer/components/Draggable";
import { useDisableDragGridItem } from "./hooks";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import { useTranslation } from "react-i18next";
import { useEmbeddedExplorerGirdContext } from "./EmbeddedExplorerGrid";

export type EmbeddedExplorerGridActionsCellProps = CellContext<Item, unknown>;

export const EmbeddedExplorerGridActionsCell = (
  params: EmbeddedExplorerGridActionsCellProps,
) => {
  const item = params.row.original;
  const { t } = useTranslation();
  const disableDrag = useDisableDragGridItem(item);
  const [isOpen, setIsOpen] = useState(false);

  const { setIsActionModalOpen, isActionModalOpen } =
    useEmbeddedExplorerGirdContext();

  if (item.upload_state === ItemUploadState.DUPLICATING) {
    return null;
  }

  const handleModalOpenChange = (value: boolean) => {
    setIsActionModalOpen(value);
  };

  return (
    <div
      onClick={(e) => {
        e.stopPropagation();
      }}
    >
      <Draggable
        id={params.cell.id}
        item={item}
        className="explorer__grid__item__actions"
        disabled={disableDrag || isActionModalOpen}
      >
        <ItemActionDropdown
          item={item}
          isOpen={isOpen}
          setIsOpen={setIsOpen}
          onModalOpenChange={handleModalOpenChange}
          trigger={
            <Button
              variant="tertiary"
              onClick={() => setIsOpen(!isOpen)}
              aria-label={t("explorer.grid.actions.button_aria_label", {
                name: item.title,
              })}
              icon={<span className="material-icons">more_horiz</span>}
              size="nano"
            />
          }
        />
      </Draggable>
    </div>
  );
};
