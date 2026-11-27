import { Item } from "@/features/drivers/types";
import { Table } from "@tanstack/react-table";
import { KeyboardEvent, useEffect, useState } from "react";
import { useGlobalExplorer } from "../components/GlobalExplorerContext";
import { useSelectionStore } from "../stores/selectionStore";

export const useTableKeyboardNavigation = ({
  table,
  tableRef,
  isDisabled = false,
  isGrid = false,
}: {
  table: Table<Item>;
  tableRef: React.RefObject<HTMLElement | null>;
  isDisabled?: boolean;
  // The items are laid out in the columns of a CSS grid rather than table rows.
  isGrid?: boolean;
}) => {
  const { itemId } = useGlobalExplorer();
  const selectionStore = useSelectionStore();
  const setSelectedItems = selectionStore.setSelectedItems;
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(
    null
  );

  useEffect(() => {
    // We want to focus on the table on load to make up/down arrows keyboard navigation work in table.
    // We also want to focus when selectedItem are updated to make sure that we case use arrows navigation after selection. ( Which is not always
    // the case by default, if we start the area selection from outside the table, the body will be focused instead of the table, making the
    // onKeyDown event not being triggered on table)

    if (isDisabled) {
      return;
    }

    const focusTable = () => {
      // Leave the focus on an item of the table, the arrows reach the table from there.
      if (
        tableRef.current &&
        !tableRef.current.contains(document.activeElement)
      ) {
        tableRef.current.focus({ preventScroll: true });
      }
    };

    // Focus initially, then whenever the selection changes. Subscribing directly
    // to the store (instead of via a hook) avoids re-rendering the caller on
    // every selection mutation during a marquee drag.
    focusTable();
    return selectionStore.subscribe(focusTable);
  }, [selectionStore, tableRef, isDisabled]);

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
      setSelectedItems([table.getRowModel().rows[0].original]);
      setLastSelectedIndex(0);
      focusItem(0);
    } else {
      // Use case example: you selected items, you delete them. You press "ArrowUp/Down", you expect to select the item that was
      // just below the last selected item, which is now deleted.
      const newSelectedIndex = cap();
      setSelectedItems([table.getRowModel().rows[newSelectedIndex].original]);
      setLastSelectedIndex(newSelectedIndex);
      focusItem(newSelectedIndex);
    }
  };

  // In the grid, the focus follows the selection so that screen readers
  // announce the item and it scrolls into view.
  const focusItem = (index: number) => {
    if (!isGrid) {
      return;
    }
    tableRef.current
      ?.querySelector<HTMLElement>(
        `[data-id="${table.getRowModel().rows[index].original.id}"]`,
      )
      ?.focus();
  };

  // Number of items per row: one in the table, the rendered columns in the grid.
  const getColumnCount = () => {
    if (!isGrid || !tableRef.current) {
      return 1;
    }
    const columns = getComputedStyle(tableRef.current).gridTemplateColumns;
    return Math.max(1, columns.split(" ").filter(Boolean).length);
  };

  // Moves the selection by `delta` items: one for the previous or next item,
  // a row's worth of items to go up or down in the grid.
  const move = (event: KeyboardEvent<HTMLElement>, delta: number) => {
    // If no item is selected, select the first item
    if (selectionStore.getSelectedItems().length === 0) {
      firstPress();
      return;
    }

    const rows = table.getRowModel().rows;
    const selectedIndices = rows
      .map((row, index) =>
        selectionStore.isSelected(row.original.id) ? index : -1,
      )
      .filter((index) => index !== -1);
    if (selectedIndices.length === 0) {
      return;
    }
    // Extending the selection downwards continues from its last item.
    const currentSelectedIndex =
      delta > 0 && event.shiftKey
        ? selectedIndices[selectedIndices.length - 1]
        : selectedIndices[0];

    let newSelectedIndex = currentSelectedIndex + delta;
    if (newSelectedIndex < 0) {
      return;
    }
    if (newSelectedIndex > rows.length - 1) {
      // Going down from the row above an incomplete last row lands on its last item.
      if (delta <= 1 || currentSelectedIndex === rows.length - 1) {
        return;
      }
      newSelectedIndex = rows.length - 1;
    }

    if (event.shiftKey) {
      // When SHIFT is pressed, keep the previous selection and add the items up to the new one
      const step = newSelectedIndex > currentSelectedIndex ? 1 : -1;
      const added: Item[] = [];
      for (
        let index = currentSelectedIndex + step;
        step > 0 ? index <= newSelectedIndex : index >= newSelectedIndex;
        index += step
      ) {
        added.push(rows[index].original);
      }
      setSelectedItems((prev) => [
        ...prev,
        ...added.filter((item) => !prev.includes(item)),
      ]);
    } else {
      // Select only the new item
      setSelectedItems([rows[newSelectedIndex].original]);
    }
    setLastSelectedIndex(newSelectedIndex);
    focusItem(newSelectedIndex);
  };

  // Handle keyboard navigation via arrows: up/down in the table, all four in the grid
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (isDisabled) {
      return;
    }
    if (event.key === "ArrowDown") {
      move(event, getColumnCount());
    } else if (event.key === "ArrowUp") {
      move(event, -getColumnCount());
    } else if (isGrid && event.key === "ArrowRight") {
      move(event, 1);
    } else if (isGrid && event.key === "ArrowLeft") {
      move(event, -1);
    } else {
      return;
    }
    // The arrows move the selection, not the page.
    if (isGrid) {
      event.preventDefault();
    }
  };

  return { onKeyDown };
};
