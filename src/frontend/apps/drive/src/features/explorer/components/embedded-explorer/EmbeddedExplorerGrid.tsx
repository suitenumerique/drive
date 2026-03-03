import { Item, ItemType } from "@/features/drivers/types";
import {
  createContext,
  Dispatch,
  SetStateAction,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import {
  CellContext,
  createColumnHelper,
  flexRender,
} from "@tanstack/react-table";
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
import { Droppable } from "@/features/explorer/components/Droppable";
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
import { SortableColumnHeader } from "./headers/SortableColumnHeader";
import { CustomizableColumnHeader } from "./headers/CustomizableColumnHeader";

export type EmbeddedExplorerGridProps = {
  isCompact?: boolean;
  enableMetaKeySelection?: boolean;
  disableItemDragAndDrop?: boolean;
  setRightPanelForcedItem?: (item: Item | undefined) => void;
  items: AppExplorerProps["childrenItems"];
  gridActionsCell?: AppExplorerProps["gridActionsCell"];
  gridNameCell?: (params: EmbeddedExplorerGridNameCellProps) => React.ReactNode;
  onNavigate: (event: NavigationEvent) => void;
  selectedItems?: Item[];
  setSelectedItems?: Dispatch<SetStateAction<Item[]>>;
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
  col1Config?: ColumnConfig;
  col2Config?: ColumnConfig;
};

const EMPTY_ARRAY: Item[] = [];
const columnHelper = createColumnHelper<Item>();

type EmbeddedExplorerGridContextType = EmbeddedExplorerGridProps & {
  selectedItemsMap: Record<string, Item>;
  openMoveModal: () => void;
  closeMoveModal: () => void;
  setMoveItem: (item: Item) => void;
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

  const selectedItems = props.selectedItems ?? [];
  const selectedItemsMap = useMemo(() => {
    const map: Record<string, Item> = {};
    selectedItems.forEach((item) => {
      map[item.id] = item;
    });
    return map;
  }, [selectedItems]);
  // TODO: This hook makes use of the ExplorerContext to manage the overred items. So, this component is not really standalone as it should be.
  const { overedItemIds, setOveredItemIds } = useDragItemContext();

  const lastSelectedRowRef = useRef<string | null>(null);

  const col1CellComponent = props.col1Config?.cell;
  const col2CellComponent = props.col2Config?.cell;

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

  const handleSortCol1 = useCallback(
    (id: string) => props.onSort?.(id as ColumnType),
    [props.onSort],
  );

  const handleSortCol2 = useCallback(
    (id: string) => props.onSort?.(id as ColumnType),
    [props.onSort],
  );

  const handleChangeCol1 = useCallback(
    (type: ColumnType) => props.onChangeColumn?.("column1", type),
    [props.onChangeColumn],
  );

  const handleChangeCol2 = useCallback(
    (type: ColumnType) => props.onChangeColumn?.("column2", type),
    [props.onChangeColumn],
  );

  const contextValue = useMemo<EmbeddedExplorerGridContextType>(
    () => ({
      ...props,
      selectedItemsMap,
      openMoveModal: moveModal.open,
      closeMoveModal: moveModal.close,
      setMoveItem,
      isActionModalOpen,
      setIsActionModalOpen,
    }),
    [
      props,
      selectedItemsMap,
      moveModal.open,
      moveModal.close,
      isActionModalOpen,
    ],
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
                <th style={{ width: props.isCompact ? undefined : "40%" }}>
                  <SortableColumnHeader
                    label={t("explorer.grid.name")}
                    columnId="title"
                    sortState={props.sortState ?? null}
                    onSort={handleSortTitle}
                  />
                </th>
                {!props.isCompact && (
                  <>
                    <th
                      className="explorer__grid__th--info-col-1"
                      style={{ width: "22%", padding: "0 8px" }}
                    >
                      {props.prefs && props.col1Config ? (
                        <CustomizableColumnHeader
                          slot="column1"
                          currentType={props.prefs.column1}
                          defaultType={DEFAULT_COLUMN_PREFERENCES.column1}
                          sortState={props.sortState ?? null}
                          onSort={handleSortCol1}
                          onChangeColumn={handleChangeCol1}
                        />
                      ) : (
                        <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable">
                          {t("explorer.grid.last_update")}
                        </div>
                      )}
                    </th>
                    <th
                      className="explorer__grid__th--info-col-2"
                      style={{ width: "22%", padding: "0 8px" }}
                    >
                      {props.prefs && props.col2Config ? (
                        <CustomizableColumnHeader
                          slot="column2"
                          currentType={props.prefs.column2}
                          defaultType={DEFAULT_COLUMN_PREFERENCES.column2}
                          sortState={props.sortState ?? null}
                          onSort={handleSortCol2}
                          onChangeColumn={handleChangeCol2}
                        />
                      ) : null}
                    </th>
                  </>
                )}
                {!props.isCompact && <th style={{ width: "5%" }}></th>}
              </tr>
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => {
                const isSelected = !!selectedItemsMap[row.original.id];
                const isOvered = !!overedItemIds[row.original.id];
                return (
                  <tr
                    key={row.original.id}
                    className={clsx("selectable", {
                      selected: isSelected,
                      over: isOvered,
                    })}
                    data-id={row.original.id}
                    tabIndex={0}
                    onClick={(e) => {
                      const target = e.target as HTMLElement;
                      const closest = target.closest("tr");
                      // Because if we use modals or other components, even with a Portal, React triggers events on the original parent.
                      // So we check that the clicked element is indeed an element of the table.
                      if (!closest) {
                        return;
                      }

                      // In SDK mode we want the popup to behave like desktop. For instance we want the simple click to
                      // trigger selection, not to open a file as it is the case on mobile.
                      const isMobile =
                        isTablet() && props.displayMode !== "sdk";

                      // Single click to select/deselect the item
                      if (!isMobile && e.detail === 1) {
                        if (!canSelect(row.original)) {
                          return;
                        }

                        if (
                          props.enableMetaKeySelection &&
                          e.shiftKey &&
                          lastSelectedRowRef.current
                        ) {
                          // Get all rows between last selected and current
                          const rows = table.getRowModel().rows;
                          const lastSelectedIndex = rows.findIndex(
                            (r) => r.id === lastSelectedRowRef.current,
                          );
                          const currentIndex = rows.findIndex(
                            (r) => r.id === row.id,
                          );

                          if (lastSelectedIndex !== -1 && currentIndex !== -1) {
                            const startIndex = Math.min(
                              lastSelectedIndex,
                              currentIndex,
                            );
                            const endIndex = Math.max(
                              lastSelectedIndex,
                              currentIndex,
                            );

                            const newSelection = [...selectedItems];
                            for (let i = startIndex; i <= endIndex; i++) {
                              if (!selectedItemsMap[rows[i].original.id]) {
                                newSelection.push(rows[i].original);
                              }
                            }

                            props.setSelectedItems?.(newSelection);
                          }
                        } else if (
                          props.enableMetaKeySelection &&
                          (e.metaKey ||
                            e.ctrlKey ||
                            props.displayMode === "sdk")
                        ) {
                          // Toggle the selected item.
                          props.setSelectedItems?.((value) => {
                            let newValue = [...value];
                            if (
                              newValue.find(
                                (item) => item.id == row.original.id,
                              )
                            ) {
                              newValue = newValue.filter(
                                (item) => item.id !== row.original.id,
                              );
                            } else {
                              newValue.push(row.original);
                            }
                            return newValue;
                          });
                          if (!isSelected) {
                            lastSelectedRowRef.current = row.id;
                          }
                        } else {
                          props.setSelectedItems?.([row.original]);
                          lastSelectedRowRef.current = row.id;
                          props.setRightPanelForcedItem?.(undefined);
                        }
                      }

                      // Double click to open the item
                      if (isMobile || e.detail === 2) {
                        if (row.original.type === ItemType.FOLDER) {
                          props.onNavigate({
                            type: NavigationEventType.ITEM,
                            item: row.original,
                          });
                        } else {
                          props.onFileClick?.(row.original);
                        }
                      }
                    }}
                    onContextMenu={(e) => {
                      if (isSelected) return;
                      e.preventDefault();
                      e.stopPropagation();
                      contextMenu.open({
                        position: { x: e.clientX, y: e.clientY },
                        items: getItemActionMenuItems(row.original),
                      });
                    }}
                  >
                    {row.getVisibleCells().map((cell, index) => {
                      const isFirstCell = index === 0;
                      return (
                        <td
                          key={cell.id}
                          className={clsx("", {
                            "c__datagrid__row__cell--actions":
                              cell.column.id === "actions",
                            "c__datagrid__row__cell--title": isFirstCell,
                          })}
                        >
                          <Droppable
                            id={cell.id}
                            item={row.original}
                            disabled={
                              isSelected ||
                              row.original.type !== ItemType.FOLDER ||
                              !row.original.abilities?.children_create
                            }
                            onOver={(isOver, item) => {
                              setOveredItemIds?.((prev) => ({
                                ...prev,
                                [row.original.id]:
                                  item.id === row.original.id ? false : isOver,
                              }));
                            }}
                          >
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext(),
                            )}
                          </Droppable>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
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
