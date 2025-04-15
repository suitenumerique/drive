import { ItemType } from "@/features/drivers/types";
import { Item } from "@/features/drivers/types";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  itemToTreeItem,
  NavigationEventType,
  useExplorer,
} from "../ExplorerContext";
import clsx from "clsx";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { Loader, useCunningham } from "@openfun/cunningham-react";
import gridEmpty from "@/assets/grid_empty.png";
import { Droppable } from "../Droppable";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { useTableKeyboardNavigation } from "../../hooks/useTableKeyboardNavigation";
import { ExplorerGridNameCell } from "./ExplorerGridNameCell";
import { ExplorerGridUpdatedAtCell } from "./ExplorerGridUpdatedAtCell";
import { ExplorerGridActionsCell } from "./ExplorerGridActionsCell";
import { ExplorerProps } from "../Explorer";

const EMPTY_ARRAY: Item[] = [];

export const ExplorerGrid = (props: ExplorerProps) => {
  const { t } = useTranslation();
  const { t: tc } = useCunningham();
  const lastSelectedRowRef = useRef<string | null>(null);
  const {
    setSelectedItems,
    selectedItems,
    selectedItemsMap,
    treeIsInitialized,
    onNavigate,
    setRightPanelForcedItem,
    itemId,
  } = useExplorer();
  const treeContext = useTreeContext();
  const columnHelper = createColumnHelper<Item>();
  const [overedItemIds, setOveredItemIds] = useState<Record<string, boolean>>(
    {}
  );

  const columns = [
    columnHelper.accessor("title", {
      header: t("explorer.grid.name"),
      cell: ExplorerGridNameCell,
    }),
    columnHelper.accessor("updated_at", {
      header: t("explorer.grid.last_update"),
      cell: ExplorerGridUpdatedAtCell,
    }),
    columnHelper.display({
      id: "actions",
      cell: props.gridActionsCell ?? ExplorerGridActionsCell,
    }),
  ];

  const folders = useMemo(() => {
    if (!props.childrenItems) {
      return [];
    }

    return props.childrenItems.filter((item) => item.type === ItemType.FOLDER);
  }, [props.childrenItems]);

  useEffect(() => {
    if (treeIsInitialized && itemId) {
      treeContext?.treeApiRef.current?.open(itemId);
      treeContext?.treeApiRef.current?.openParents(itemId);
    }
  }, [itemId, treeIsInitialized]);

  useEffect(() => {
    if (!treeIsInitialized || !itemId) {
      return;
    }
    // We merge the existing children with the new folders or we create the children
    const childrens = folders.map((folder) => {
      const folderNode = treeContext?.treeData.getNode(folder.id);
      if (folderNode) {
        const children = folderNode.children?.map((child) => child) as Item[];
        const item = itemToTreeItem({
          ...folder,
          children: children,
        });
        item.hasLoadedChildren = true;
        return item;
      } else {
        const children = itemToTreeItem({
          ...folder,
          children: [],
        });

        return children;
      }
    });

    treeContext?.treeData.setChildren(itemId, childrens);
  }, [folders, treeIsInitialized]);

  const table = useReactTable({
    data: props.childrenItems ?? EMPTY_ARRAY,
    columns,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
  });

  const isLoading = props.childrenItems === undefined;
  const isEmpty = table.getRowModel().rows.length === 0;
  const tableRef = useRef<HTMLTableElement>(null);
  const { onKeyDown } = useTableKeyboardNavigation({
    table,
    tableRef,
  });

  const getContent = () => {
    if (isLoading) {
      return <Loader aria-label={tc("components.datagrid.loader_aria")} />;
    }
    if (isEmpty) {
      return (
        <div className="c__datagrid__empty-placeholder fs-h3 clr-greyscale-900 fw-bold">
          <img src={gridEmpty.src} alt={t("components.datagrid.empty_alt")} />
          <div className="explorer__grid__empty">
            <div className="explorer__grid__empty__caption">
              {t("explorer.grid.empty.caption")}
            </div>
            <div className="explorer__grid__empty__cta">
              {t("explorer.grid.empty.cta")}
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="c__datagrid__table__container">
        <table ref={tableRef} tabIndex={0} onKeyDown={onKeyDown}>
          <thead>
            <tr>
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
              <th></th>
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

                    // Single click to select/deselect the item
                    if (e.detail === 1) {
                      if (e.shiftKey && lastSelectedRowRef.current) {
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

                          setSelectedItems(newSelection);
                        }
                      } else if (e.metaKey || e.ctrlKey) {
                        // Toggle the selected item.
                        setSelectedItems((value) => {
                          let newValue = [...value];
                          if (
                            newValue.find((item) => item.id == row.original.id)
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
                        setSelectedItems([row.original]);
                        lastSelectedRowRef.current = row.id;
                        setRightPanelForcedItem(row.original);
                      }
                    }

                    // Double click to open the item
                    if (e.detail === 2) {
                      if (row.original.type === ItemType.FOLDER) {
                        onNavigate({
                          type: NavigationEventType.ITEM,
                          item: row.original,
                        });
                      } else {
                        if (row.original.url) {
                          window.open(row.original.url, "_blank");
                        } else {
                          addToast(
                            <ToasterItem>
                              {t("explorer.grid.no_url")}
                            </ToasterItem>
                          );
                        }
                      }
                    }
                  }}
                >
                  {row.getVisibleCells().map((cell, index, array) => {
                    const isLastCell = index === array.length - 1;
                    const isFirstCell = index === 0;
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
                          disabled={row.original.type !== ItemType.FOLDER}
                          onOver={(isOver, item) => {
                            setOveredItemIds((prev) => ({
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
    );
  };

  return (
    <div
      className={clsx("c__datagrid explorer__grid", {
        "c__datagrid--empty": isEmpty,
        "c__datagrid--loading": isLoading,
      })}
    >
      {getContent()}
    </div>
  );
};
