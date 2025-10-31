import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import { useState } from "react";
import { Button } from "@openfun/cunningham-react";
import { Draggable } from "@/features/explorer/components/Draggable";
import { useDisableDragGridItem } from "./hooks";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";

export type EmbeddedExplorerGridActionsCellProps = CellContext<Item, unknown>;

export const EmbeddedExplorerGridActionsCell = (
  params: EmbeddedExplorerGridActionsCellProps
) => {
  const item = params.row.original;
  const disableDrag = useDisableDragGridItem(item);
  const [isOpen, setIsOpen] = useState(false);

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
        disabled={disableDrag}
      >
        <ItemActionDropdown
          item={item}
          isOpen={isOpen}
          setIsOpen={setIsOpen}
          trigger={
            <Button
              variant="tertiary"
              onClick={() => setIsOpen(!isOpen)}
              icon={<span className="material-icons">more_horiz</span>}
            />
          }
        />
      </Draggable>
    </div>
  );
};
