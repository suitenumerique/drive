import { Item, ItemType, ItemUploadState } from "@/features/drivers/types";
import {
  createContext,
  Dispatch,
  SetStateAction,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import { createColumnHelper, flexRender } from "@tanstack/react-table";
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
import { EmbeddedExplorerGridUpdatedAtCell } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridUpdatedAtCell";
import { EmbeddedExplorerGridActionsCell } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridActionsCell";
import { useTableKeyboardNavigation } from "@/features/explorer/hooks/useTableKeyboardNavigation";
import clsx from "clsx";
import { isTablet } from "@/features/ui/components/responsive/ResponsiveDivs";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { Droppable } from "@/features/explorer/components/Droppable";
import { useDragItemContext } from "@/features/explorer/components/ExplorerDndProvider";
import { useModal } from "@openfun/cunningham-react";
import { ExplorerMoveFolder } from "@/features/explorer/components/modals/move/ExplorerMoveFolderModal";
import { ItemInfo } from "@/features/items/components/ItemInfo";
import {
  FilePreview,
  FilePreviewType,
} from "@/features/ui/preview/files-preview/FilesPreview";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { EmbeddedExplorerContextMenu } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerContextMenu";

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
  openPreviews?: boolean;
};

const EMPTY_ARRAY: Item[] = [];

type EmbeddedExplorerGridContextType = EmbeddedExplorerGridProps & {
  selectedItemsMap: Record<string, Item>;
  openMoveModal: () => void;
  closeMoveModal: () => void;
  setMoveItem: (item: Item) => void;
};

export const EmbeddedExplorerGridContext = createContext<
  EmbeddedExplorerGridContextType | undefined
>(undefined);

export const useEmbeddedExplorerGirdContext = () => {
  const context = useContext(EmbeddedExplorerGridContext);
  if (!context) {
    throw new Error(
      "useEmbeddedExplorerGirdContext must be used within an EmbeddedExplorerGridContext"
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

  const openPreviews = props.openPreviews ?? true;
  const [moveItem, setMoveItem] = useState<Item | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [openedFileId, setOpenedFileId] = useState<string | undefined>(
    undefined
  );
  const [currentPreviewItem, setCurrentPreviewItem] = useState<
    Item | undefined
  >(undefined);
  const [contextMenuState, setContextMenuState] = useState<{
    isOpen: boolean;
    item: Item | null;
    position: { x: number; y: number };
  }>({
    isOpen: false,
    item: null,
    position: { x: 0, y: 0 },
  });
  const moveModal = useModal();
  const { handleDownloadItem } = useDownloadItem();

  const handleClosePreview = () => {
    setIsPreviewOpen(false);
    setOpenedFileId(undefined);
  };

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
  const columnHelper = createColumnHelper<Item>();
  const columns = [
    columnHelper.display({
      id: "mobile",
      cell: EmbeddedExplorerGridMobileCell,
    }),
    columnHelper.accessor("title", {
      header: t("explorer.grid.name"),
      cell: props.gridNameCell ?? EmbeddedExplorerGridNameCell,
    }),
    columnHelper.accessor("updated_at", {
      header: t("explorer.grid.last_update"),
      cell: EmbeddedExplorerGridUpdatedAtCell,
    }),
    ...(props.isCompact
      ? []
      : [
          columnHelper.display({
            id: "actions",
            cell: props.gridActionsCell ?? EmbeddedExplorerGridActionsCell,
          }),
        ]),
  ];

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
  });

  const handleCloseMoveModal = () => {
    moveModal.close();
    setMoveItem(null);
  };

  const canSelect = props.canSelect ?? (() => true);

  const handleChangePreviewItem = (file?: FilePreviewType) => {
    if (file) {
      const item = props.items?.find((item) => file?.id === item.id);
      setCurrentPreviewItem(item);
    } else {
      setCurrentPreviewItem(undefined);
    }
  };

  const handleDownloadFile = () => {
    handleDownloadItem(currentPreviewItem);
  };

  const handleContextMenu = (e: React.MouseEvent, item: Item) => {
    e.preventDefault();
    e.stopPropagation();

    setContextMenuState({
      isOpen: true,
      item,
      position: { x: e.clientX, y: e.clientY },
    });
  };

  const handleCloseContextMenu = () => {
    setContextMenuState({
      isOpen: false,
      item: null,
      position: { x: 0, y: 0 },
    });
  };

  const previewItems: FilePreviewType[] = useMemo(() => {
    const items =
      props.items?.filter((item) => item.type === ItemType.FILE) ?? [];
    return items?.map((item) => ({
      id: item.id,
      title: item.title,
      mimetype: item.mimetype ?? "",
      url: item.url ?? "",
      isSuspicious: item.upload_state === ItemUploadState.SUSPICIOUS,
    }));
  }, [props.items]);

  return (
    <>
      {/* The context is only here to avoid the rerendering of react table cells
      when passing props to cells, with a context // we avoid that by passing
      props via context, but it's quite overkill, unfortunatly we did not find a
      better solution. */}
      <EmbeddedExplorerGridContext.Provider
        value={{
          ...props,
          selectedItemsMap,
          openMoveModal: moveModal.open,
          closeMoveModal: moveModal.close,
          setMoveItem,
        }}
      >
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
                <th style={{ width: "50%" }}>
                  <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable">
                    {t("explorer.grid.name")}
                  </div>
                </th>
                <th>
                  <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable">
                    {t("explorer.grid.last_update")}
                  </div>
                </th>
                {!props.isCompact && <th></th>}
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
                    onContextMenu={(e) => handleContextMenu(e, row.original)}
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
                            (r) => r.id === lastSelectedRowRef.current
                          );
                          const currentIndex = rows.findIndex(
                            (r) => r.id === row.id
                          );

                          if (lastSelectedIndex !== -1 && currentIndex !== -1) {
                            const startIndex = Math.min(
                              lastSelectedIndex,
                              currentIndex
                            );
                            const endIndex = Math.max(
                              lastSelectedIndex,
                              currentIndex
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
                                (item) => item.id == row.original.id
                              )
                            ) {
                              newValue = newValue.filter(
                                (item) => item.id !== row.original.id
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
                          if (openPreviews) {
                            if (row.original.url) {
                              setIsPreviewOpen(true);
                              setOpenedFileId(row.original.id);
                            } else {
                              addToast(
                                <ToasterItem>
                                  {t("explorer.grid.no_url")}
                                </ToasterItem>
                              );
                            }
                          }
                        }
                      }
                    }}
                  >
                    {row.getVisibleCells().map((cell, index, array) => {
                      const isLastCell = index === array.length - 1;
                      const isFirstCell = index === 0;
                      // Check if the item is selected, if so, we can't drop an item inside it
                      const isSelected = !!selectedItemsMap[row.original.id];
                      return (
                        <td
                          key={cell.id}
                          className={clsx("", {
                            "c__datagrid__row__cell--actions": isLastCell,
                            "c__datagrid__row__cell--title": isFirstCell,
                          })}
                        >
                          <Droppable
                            id={cell.id}
                            item={row.original}
                            disabled={
                              isSelected ||
                              row.original.type !== ItemType.FOLDER ||
                              !row.original.abilities.children_create
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
                              cell.getContext()
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
        <FilePreview
          isOpen={isPreviewOpen}
          onClose={handleClosePreview}
          title={t("file_preview.title")}
          files={previewItems ?? []}
          onChangeFile={handleChangePreviewItem}
          handleDownloadFile={handleDownloadFile}
          openedFileId={openedFileId}
          sidebarContent={
            currentPreviewItem && <ItemInfo item={currentPreviewItem} />
          }
        />
        {moveModal.isOpen && moveItem && (
          <ExplorerMoveFolder
            {...moveModal}
            onClose={handleCloseMoveModal}
            itemsToMove={[moveItem]}
            initialFolderId={props.parentItem?.id}
          />
        )}
        {contextMenuState.isOpen && contextMenuState.item && (
          <EmbeddedExplorerContextMenu
            item={contextMenuState.item}
            parentItem={props.parentItem}
            onNavigate={props.onNavigate}
            setRightPanelForcedItem={props.setRightPanelForcedItem}
            setRightPanelOpen={(open) => {
              // You might need to implement this based on your right panel implementation
              console.log("Right panel open:", open);
            }}
            position={contextMenuState.position}
            onClose={handleCloseContextMenu}
          />
        )}
      </EmbeddedExplorerGridContext.Provider>
    </>
  );
};
