import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSelectionStore } from "@/features/explorer/stores/selectionStore";
import { useTranslation } from "react-i18next";
import { CellContext, createColumnHelper, Row } from "@tanstack/react-table";
import { useReactTable } from "@tanstack/react-table";
import { getCoreRowModel } from "@tanstack/react-table";
import { AppExplorerProps } from "@/features/explorer/components/app-view/AppExplorer";
import {
  GlobalExplorerContextType,
  NavigationEvent,
  NavigationEventType,
} from "@/features/explorer/components/GlobalExplorerContext";
import { EmbeddedExplorerGridMobileCell } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridMobileCell";
import {
  EmbeddedExplorerGridNameCell,
  EmbeddedExplorerGridNameCellProps,
} from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridNameCell";
import { EmbeddedExplorerGridActionsCell } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridActionsCell";
import { useTableKeyboardNavigation } from "@/features/explorer/hooks/useTableKeyboardNavigation";
import clsx from "clsx";
import { isTablet } from "@/features/ui/components/responsive/ResponsiveDivs";
import { useDragItemContext } from "@/features/explorer/components/ExplorerDndProvider";
import { useModal } from "@gouvfr-lasuite/cunningham-react";
import { ExplorerMoveFolder } from "@/features/explorer/components/modals/move/ExplorerMoveFolderModal";
import { useContextMenuContext } from "@gouvfr-lasuite/ui-kit";
import { useItemActionMenuItems } from "../../hooks/useItemActionMenuItems";
import {
  ColumnConfig,
  ColumnPreferences,
  ColumnType,
  DEFAULT_COLUMN_PREFERENCES,
  SortState,
} from "../../types/columns";
import { ColumnHeader } from "./headers/ColumnHeader";
import { CustomizableColumnHeader } from "./headers/CustomizableColumnHeader";
import { useDuplicatingItemsPoller } from "../../hooks/useDuplicatingItemsPoller";
import { EmbeddedExplorerGridRow } from "./EmbeddedExplorerGridRow";
import posthog from "posthog-js";

const POSTHOG_EVENT_COLUMN_TYPE_CHANGED = "column_type_changed";

export type EmbeddedExplorerGridProps = {
  isCompact?: boolean;
  enableMetaKeySelection?: boolean;
  disableItemDragAndDrop?: boolean;
  setRightPanelForcedItem?: (item: Item | undefined) => void;
  items: AppExplorerProps["childrenItems"];
  gridActionsCell?: AppExplorerProps["gridActionsCell"];
  gridNameCell?: (params: EmbeddedExplorerGridNameCellProps) => React.ReactNode;
  onNavigate: (event: NavigationEvent) => void;
  parentItem?: Item;
  displayMode?: GlobalExplorerContextType["displayMode"];
  canSelect?: (item: Item) => boolean;
  onFileClick?: (item: Item) => void;
  disableKeyboardNavigation?: boolean;
  // Custom columns
  sortState?: SortState;
  onSort?: (columnId: "title" | ColumnType) => void;
  prefs?: ColumnPreferences;
  onChangeColumn?: (slot: "column1" | "column2", type: ColumnType) => void;
  column1Config?: ColumnConfig;
  column2Config?: ColumnConfig;
  viewSortable?: boolean;
};

const EMPTY_ARRAY: Item[] = [];
const columnHelper = createColumnHelper<Item>();

// Only the fields actually consumed by cells/hooks — keeping this narrow so
// that the memoized context value stays stable across parent re-renders.
// Adding fields here means cells will re-render on every parent tick that
// changes them, so treat new additions with care.
type EmbeddedExplorerGridContextType = {
  disableItemDragAndDrop?: boolean;
  isActionModalOpen: boolean;
  setIsActionModalOpen: (value: boolean) => void;
};

export const EmbeddedExplorerGridContext = createContext<
  EmbeddedExplorerGridContextType | undefined
>(undefined);

export const useEmbeddedExplorerGirdContext = () => {
  const context = useContext(EmbeddedExplorerGridContext);
  if (!context) {
    throw new Error(
      "useEmbeddedExplorerGirdContext must be used within an EmbeddedExplorerGridContext",
    );
  }
  return context;
};

/**
 * Standalone component to display a list of items in a table.
 *
 * It provides:
 * - Compact and Full mode
 * - Keyboard navigation
 * - Selection
 * - Over
 * - Actions
 * - Mobile support
 * - Table support
 * - Droppable support
 * - Right panel support
 */
export const EmbeddedExplorerGrid = (props: EmbeddedExplorerGridProps) => {
  const { t } = useTranslation();

  const [moveItem, setMoveItem] = useState<Item | null>(null);
  const moveModal = useModal();
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const { getMenuItems: getItemActionMenuItems, modals: itemActionModals } =
    useItemActionMenuItems({
      onModalOpenChange: setIsActionModalOpen,
    });
  const contextMenu = useContextMenuContext();

  useDuplicatingItemsPoller(props.items ?? EMPTY_ARRAY);

  const selectionStore = useSelectionStore();
  // TODO: This hook makes use of the ExplorerContext to manage the overred items. So, this component is not really standalone as it should be.
  const { overedItemIds, setOveredItemIds } = useDragItemContext();

  const lastSelectedRowRef = useRef<string | null>(null);

  const col1CellComponent = props.column1Config?.cell;
  const col2CellComponent = props.column2Config?.cell;

  const columns = useMemo(
    () => [
      columnHelper.display({
        id: "mobile",
        cell: EmbeddedExplorerGridMobileCell,
      }),
      columnHelper.accessor("title", {
        id: "title",
        header: t("explorer.grid.name"),
        cell: props.gridNameCell ?? EmbeddedExplorerGridNameCell,
      }),
      ...(props.isCompact
        ? []
        : [
            columnHelper.display({
              id: "info-col-1",
              cell: col1CellComponent ?? EmbeddedExplorerGridMobileCell,
            }),
            columnHelper.display({
              id: "info-col-2",
              cell: col2CellComponent ?? EmbeddedExplorerGridMobileCell,
            }),
            columnHelper.display({
              id: "actions",
              cell: props.gridActionsCell ?? EmbeddedExplorerGridActionsCell,
            }),
          ]),
    ],

    [col1CellComponent, col2CellComponent, props.isCompact],
  );

  const table = useReactTable({
    data: props.items ?? EMPTY_ARRAY,
    columns,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
  });

  const tableRef = useRef<HTMLTableElement>(null);
  const { onKeyDown } = useTableKeyboardNavigation({
    table,
    tableRef,
    isDisabled: isActionModalOpen || props.disableKeyboardNavigation,
  });

  const handleCloseMoveModal = () => {
    moveModal.close();
    setMoveItem(null);
  };

  const canSelect = props.canSelect ?? (() => true);

  const handleSortTitle = useCallback(
    (id: string) => props.onSort?.(id as "title" | ColumnType),
    [props.onSort],
  );

  const handleSortColumn = useCallback(
    (id: string) => props.onSort?.(id as ColumnType),
    [props.onSort],
  );

  const handleChangeCol1 = useCallback(
    (type: ColumnType) => {
      posthog.capture(POSTHOG_EVENT_COLUMN_TYPE_CHANGED, {
        slot: "column1",
        new_type: type,
        previous_type: props.prefs?.column1,
      });
      props.onChangeColumn?.("column1", type);
    },
    [props.onChangeColumn, props.prefs?.column1],
  );

  const handleChangeCol2 = useCallback(
    (type: ColumnType) => {
      posthog.capture(POSTHOG_EVENT_COLUMN_TYPE_CHANGED, {
        slot: "column2",
        new_type: type,
        previous_type: props.prefs?.column2,
      });
      props.onChangeColumn?.("column2", type);
    },
    [props.onChangeColumn, props.prefs?.column2],
  );

  const contextValue = useMemo<EmbeddedExplorerGridContextType>(
    () => ({
      disableItemDragAndDrop: props.disableItemDragAndDrop,
      isActionModalOpen,
      setIsActionModalOpen,
    }),
    [props.disableItemDragAndDrop, isActionModalOpen],
  );

  const applyShiftRangeSelect = useCallback(
    (row: Row<Item>) => {
      const rows = table.getRowModel().rows;
      const lastSelectedIndex = rows.findIndex(
        (r) => r.id === lastSelectedRowRef.current,
      );
      const currentIndex = rows.findIndex((r) => r.id === row.id);
      if (lastSelectedIndex === -1 || currentIndex === -1) {
        return;
      }

      const startIndex = Math.min(lastSelectedIndex, currentIndex);
      const endIndex = Math.max(lastSelectedIndex, currentIndex);
      const newSelection = [...selectionStore.getSelectedItems()];
      for (let i = startIndex; i <= endIndex; i++) {
        if (!selectionStore.isSelected(rows[i].original.id)) {
          newSelection.push(rows[i].original);
        }
      }
      selectionStore.setSelectedItems(newSelection);
    },
    [selectionStore, table],
  );

  const toggleRowSelection = useCallback(
    (row: Row<Item>) => {
      const wasSelected = selectionStore.isSelected(row.original.id);
      selectionStore.setSelectedItems((value) => {
        if (value.some((item) => item.id === row.original.id)) {
          return value.filter((item) => item.id !== row.original.id);
        }
        return [...value, row.original];
      });
      if (!wasSelected) {
        lastSelectedRowRef.current = row.id;
      }
    },
    [selectionStore],
  );

  const replaceRowSelection = useCallback(
    (row: Row<Item>) => {
      selectionStore.setSelectedItems([row.original]);
      lastSelectedRowRef.current = row.id;
      props.setRightPanelForcedItem?.(undefined);
    },
    [selectionStore, props.setRightPanelForcedItem],
  );

  const openRow = useCallback(
    (row: Row<Item>) => {
      if (row.original.type === ItemType.FOLDER) {
        props.onNavigate({
          type: NavigationEventType.ITEM,
          item: row.original,
        });
      } else {
        props.onFileClick?.(row.original);
      }
    },
    [props.onNavigate, props.onFileClick],
  );

  const handleRowClick = useCallback(
    (e: React.MouseEvent<HTMLTableRowElement>, row: Row<Item>) => {
      if (row.original.upload_state === ItemUploadState.DUPLICATING) {
        return;
      }

      // Because if we use modals or other components, even with a Portal, React triggers events on the original parent.
      // So we check that the clicked element is indeed an element of the table.
      if (!(e.target as HTMLElement).closest("tr")) {
        return;
      }

      // In SDK mode we want the popup to behave like desktop. For instance we want the simple click to
      // trigger selection, not to open a file as it is the case on mobile.
      const isMobile = isTablet() && props.displayMode !== "sdk";

      if (isMobile || e.detail === 2) {
        openRow(row);
        return;
      }

      if (e.detail !== 1 || !canSelect(row.original)) {
        return;
      }

      const metaActive =
        props.enableMetaKeySelection &&
        (e.metaKey || e.ctrlKey || props.displayMode === "sdk");

      if (
        props.enableMetaKeySelection &&
        e.shiftKey &&
        lastSelectedRowRef.current
      ) {
        applyShiftRangeSelect(row);
      } else if (metaActive) {
        toggleRowSelection(row);
      } else {
        replaceRowSelection(row);
      }
    },
    [
      props.displayMode,
      props.enableMetaKeySelection,
      canSelect,
      openRow,
      applyShiftRangeSelect,
      toggleRowSelection,
      replaceRowSelection,
    ],
  );

  const handleRowContextMenu = useCallback(
    (e: React.MouseEvent<HTMLTableRowElement>, row: Row<Item>) => {
      if (props.displayMode === "sdk") {
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      if (row.original.upload_state === ItemUploadState.DUPLICATING) {
        return;
      }

      selectionStore.setSelectedItems([row.original]);

      contextMenu.open({
        position: { x: e.clientX, y: e.clientY },
        items: getItemActionMenuItems(row.original),
      });
    },
    [props.displayMode, selectionStore, contextMenu, getItemActionMenuItems],
  );

  const handleRowOver = useCallback(
    (rowId: string, isOver: boolean, draggedItem: Item) => {
      setOveredItemIds?.((prev) => ({
        ...prev,
        [rowId]: draggedItem.id === rowId ? false : isOver,
      }));
    },
    [setOveredItemIds],
  );

  return (
    <>
      {/* The context is only here to avoid the rerendering of react table cells
      when passing props to cells, with a context // we avoid that by passing
      props via context, but it's quite overkill, unfortunatly we did not find a
      better solution. */}
      <EmbeddedExplorerGridContext.Provider value={contextValue}>
        <div
          className={clsx("c__datagrid__table__container", {
            explorer__compact: props.isCompact,
          })}
        >
          <table ref={tableRef} tabIndex={0} onKeyDown={onKeyDown}>
            <thead>
              <tr>
                {/* This one stands for the mobile column */}
                <th></th>
                <th className="explorer__grid__th--title">
                  <ColumnHeader
                    label={t("explorer.grid.name")}
                    columnId="title"
                    sortState={props.sortState ?? null}
                    onSort={handleSortTitle}
                    sortable={props.viewSortable !== false}
                  />
                </th>
                {!props.isCompact && (
                  <>
                    <th className="explorer__grid__th--info-col-1">
                      {props.prefs && props.column1Config ? (
                        <CustomizableColumnHeader
                          slot="column1"
                          currentType={props.prefs.column1}
                          defaultType={DEFAULT_COLUMN_PREFERENCES.column1}
                          sortState={props.sortState ?? null}
                          onSort={handleSortColumn}
                          onChangeColumn={handleChangeCol1}
                          otherColumnType={props.prefs.column2}
                          sortable={props.viewSortable !== false}
                        />
                      ) : (
                        <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable">
                          {t("explorer.grid.last_update")}
                        </div>
                      )}
                    </th>
                    <th className="explorer__grid__th--info-col-2">
                      {props.prefs && props.column2Config ? (
                        <CustomizableColumnHeader
                          slot="column2"
                          currentType={props.prefs.column2}
                          defaultType={DEFAULT_COLUMN_PREFERENCES.column2}
                          sortState={props.sortState ?? null}
                          onSort={handleSortColumn}
                          onChangeColumn={handleChangeCol2}
                          otherColumnType={props.prefs.column1}
                          sortable={props.viewSortable !== false}
                        />
                      ) : null}
                    </th>
                  </>
                )}
                {!props.isCompact && (
                  <th className="explorer__grid__th--actions"></th>
                )}
              </tr>
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <EmbeddedExplorerGridRow
                  key={row.original.id}
                  row={row}
                  isOvered={!!overedItemIds[row.original.id]}
                  onClickRow={handleRowClick}
                  onContextMenuRow={handleRowContextMenu}
                  onOver={handleRowOver}
                />
              ))}
            </tbody>
          </table>
        </div>
        {moveModal.isOpen && moveItem && (
          <ExplorerMoveFolder
            {...moveModal}
            onClose={handleCloseMoveModal}
            itemsToMove={[moveItem]}
            initialFolderId={props.parentItem?.id}
          />
        )}
        {itemActionModals}
      </EmbeddedExplorerGridContext.Provider>
    </>
  );
};

export type EmbeddedExplorerGridTypeCellProps = CellContext<Item, string> & {
  children?: React.ReactNode;
};
