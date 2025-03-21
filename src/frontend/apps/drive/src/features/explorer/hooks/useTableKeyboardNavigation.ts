import { Item } from "@/features/drivers/types";
import { Table } from "@tanstack/react-table";
import { KeyboardEvent, useEffect, useState } from "react";
import { useExplorer } from "../components/ExplorerContext";

export const useTableKeyboardNavigation = ({
  table,
  tableRef,
}: {
  table: Table<Item>;
  tableRef: React.RefObject<HTMLTableElement | null>;
}) => {
  const { setSelectedItemIds, selectedItemIds, selectedItems, itemId } =
    useExplorer();
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(
    null
  );

  useEffect(() => {
    // We want to focus on the table on load to make up/down arrows keyboard navigation work in table.
    // We also want to focus when selectedItem are updated to make sure that we case use arrows navigation after selection. ( Which is not always
    // the case by default, if we start the area selection from outside the table, the body will be focused instead of the table, making the
    // onKeyDown event not being triggered on table)
    if (tableRef.current) {
      tableRef.current.focus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableRef.current, selectedItemIds]);

  useEffect(() => {
    // When we change item during navigation, the first arrow trigger must select the first item. Reset the state.
    if (itemId) {
      setLastSelectedIndex(null);
    }
  }, [itemId]);

  const cap = () => {
    let newSelectedIndex = lastSelectedIndex! > 0 ? lastSelectedIndex! - 1 : 0;
    if (newSelectedIndex > table.getRowModel().rows.length - 1) {
      // Use case: you shift + up from the bottom of the table, you delete the items.
      // newSelectedIndex will be > than the size of the table.
      // To prevent selecting row index that does not exist anymore,
      // we cap the newSelectedIndex to the size of the table.
      newSelectedIndex = table.getRowModel().rows.length - 1;
    }
    return newSelectedIndex;
  };

  const firstPress = () => {
    if (lastSelectedIndex === null) {
      // Use case: the page just displayed, you press "ArrowUp/Down", you expect to select the first item.
      setSelectedItemIds({
        [table.getRowModel().rows[0].original.id]: true,
      });
      setLastSelectedIndex(0);
    } else {
      // Use case example: you selected items, you delete them. You press "ArrowUp/Down", you expect to select the item that was
      // just below the last selected item, which is now deleted.
      const newSelectedIndex = cap();
      setSelectedItemIds({
        [table.getRowModel().rows[newSelectedIndex].original.id]: true,
      });
      setLastSelectedIndex(newSelectedIndex);
    }
  };

  const arrowUp = (event: KeyboardEvent<HTMLTableElement>) => {
    // If no item is selected, select the first item
    if (selectedItems.length === 0) {
      firstPress();
    } else {
      // Find the current selected item index
      const rows = table.getRowModel().rows;
      const currentSelectedIndex = rows.findIndex(
        (row) => selectedItemIds[row.original.id]
      );

      // If we found the current selected item and there's a previous row
      if (currentSelectedIndex !== -1 && currentSelectedIndex > 0) {
        // Get the previous row's ID
        const newSelectedIndex = currentSelectedIndex - 1;
        const prevRowId = rows[newSelectedIndex].original.id;

        if (event.shiftKey) {
          // When SHIFT is pressed, keep the previous selection and add the new one
          setSelectedItemIds({
            ...selectedItemIds,
            [prevRowId]: true,
          });
        } else {
          // Select only the previous row
          setSelectedItemIds({
            [prevRowId]: true,
          });
        }
        setLastSelectedIndex(newSelectedIndex);
      }
    }
  };

  const arrowDown = (event: KeyboardEvent<HTMLTableElement>) => {
    // If no item is selected, select the first item
    if (selectedItems.length === 0) {
      firstPress();
    } else {
      // Find the current selected item index
      const rows = table.getRowModel().rows;

      let currentSelectedIndex = -1;
      if (event.shiftKey) {
        // Get the last selected item index when using shift key
        const selectedIndices = rows
          .map((row, index) => (selectedItemIds[row.original.id] ? index : -1))
          .filter((index) => index !== -1);
        currentSelectedIndex =
          selectedIndices.length > 0
            ? selectedIndices[selectedIndices.length - 1]
            : -1;
      } else {
        currentSelectedIndex = rows.findIndex(
          (row) => selectedItemIds[row.original.id]
        );
      }

      // If we found the current selected item and there's a next row
      if (
        currentSelectedIndex !== -1 &&
        currentSelectedIndex < rows.length - 1
      ) {
        // Get the next row's ID
        const newSelectedIndex = currentSelectedIndex + 1;
        const nextRowId = rows[newSelectedIndex].original.id;

        if (event.shiftKey) {
          // When SHIFT is pressed, keep the previous selection and add the new one
          setSelectedItemIds({
            ...selectedItemIds,
            [nextRowId]: true,
          });
        } else {
          // Select only the next row
          setSelectedItemIds({
            [nextRowId]: true,
          });
        }
        setLastSelectedIndex(newSelectedIndex);
      }
    }
  };

  // Handle keyboard navigation via up/down arrows
  const onKeyDown = (event: KeyboardEvent<HTMLTableElement>) => {
    if (event.key === "ArrowDown") {
      arrowDown(event);
    } else if (event.key === "ArrowUp") {
      arrowUp(event);
    }
  };

  return { onKeyDown };
};
