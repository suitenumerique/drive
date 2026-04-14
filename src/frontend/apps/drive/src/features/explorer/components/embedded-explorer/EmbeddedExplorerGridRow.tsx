import { memo } from "react";
import { Row, flexRender } from "@tanstack/react-table";
import clsx from "clsx";
import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import { Droppable } from "@/features/explorer/components/Droppable";
import { useIsItemSelected } from "@/features/explorer/stores/selectionStore";

export type EmbeddedExplorerGridRowProps = {
  row: Row<Item>;
  isOvered: boolean;
  onClickRow: (e: React.MouseEvent<HTMLTableRowElement>, row: Row<Item>) => void;
  onContextMenuRow: (
    e: React.MouseEvent<HTMLTableRowElement>,
    row: Row<Item>,
  ) => void;
  onOver: (rowId: string, isOver: boolean, draggedItem: Item) => void;
};

const EmbeddedExplorerGridRowComponent = ({
  row,
  isOvered,
  onClickRow,
  onContextMenuRow,
  onOver,
}: EmbeddedExplorerGridRowProps) => {
  const item = row.original;
  const isSelected = useIsItemSelected(item.id);

  return (
    <tr
      className={clsx({
        selectable: item.upload_state !== ItemUploadState.DUPLICATING,
        selected: isSelected,
        over: isOvered,
        duplicating: item.upload_state === ItemUploadState.DUPLICATING,
      })}
      data-id={item.id}
      tabIndex={0}
      onClick={(e) => onClickRow(e, row)}
      onContextMenu={(e) => onContextMenuRow(e, row)}
    >
      {row.getVisibleCells().map((cell, index) => {
        const isFirstCell = index === 0;
        return (
          <td
            key={cell.id}
            className={clsx("", {
              "c__datagrid__row__cell--actions": cell.column.id === "actions",
              "c__datagrid__row__cell--title": isFirstCell,
            })}
          >
            <Droppable
              id={cell.id}
              item={item}
              disabled={
                isSelected ||
                item.type !== ItemType.FOLDER ||
                !item.abilities?.children_create
              }
              onOver={(isOver, draggedItem) =>
                onOver(item.id, isOver, draggedItem)
              }
            >
              {flexRender(cell.column.columnDef.cell, cell.getContext())}
            </Droppable>
          </td>
        );
      })}
    </tr>
  );
};

export const EmbeddedExplorerGridRow = memo(EmbeddedExplorerGridRowComponent);
