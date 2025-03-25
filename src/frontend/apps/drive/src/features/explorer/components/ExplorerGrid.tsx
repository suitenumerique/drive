import { ItemType } from "@/features/drivers/types";
import { Item } from "@/features/drivers/types";
import {
  CellContext,
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import clsx from "clsx";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import {
  Button,
  Loader,
  Tooltip,
  useCunningham,
  useModal,
} from "@openfun/cunningham-react";
import gridEmpty from "@/assets/grid_empty.png";
import { timeAgo } from "../utils/utils";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { ItemIcon } from "./ItemIcon";
import { useMutationDeleteItems } from "../hooks/useMutations";
import { useTableKeyboardNavigation } from "../hooks/useTableKeyboardNavigation";
import { ExplorerRenameItemModal } from "./modals/ExplorerRenameItemModal";

export const ExplorerGrid = () => {
  const { t } = useTranslation();
  const { t: tc } = useCunningham();
  const lastSelectedRowRef = useRef<string | null>(null);
  const columnHelper = createColumnHelper<Item>();

  // Memorize this callback is used to avoid flickering on this cell, especially with the
  // icon as <img> which get re-fetched on every render.
  const nameCellRenderer = useCallback(
    (params: CellContext<Item, string>) => (
      <ItemTitle item={params.row.original} />
    ),
    []
  );

  const { setSelectedItemIds, selectedItemIds, onNavigate, children, item } =
    useExplorer();

  const [renameItem, setRenameItem] = useState<Item>();
  const renameModal = useModal();

  const actionsCell = useCallback((params: CellContext<Item, unknown>) => {
    return (
      <ItemActions
        item={params.row.original}
        onRename={() => {
          setRenameItem(params.row.original);
          renameModal.open();
        }}
      />
    );
  }, []);

  const columns = [
    columnHelper.accessor("title", {
      header: t("explorer.grid.name"),
      cell: nameCellRenderer,
    }),
    columnHelper.accessor("updated_at", {
      header: t("explorer.grid.last_update"),
      cell: (info) => (
        <div className="explorer__grid__item__last-update">
          <Tooltip content={info.row.original.updated_at.toLocaleString()}>
            <span>{timeAgo(info.row.original.updated_at)}</span>
          </Tooltip>
        </div>
      ),
    }),
    columnHelper.display({
      id: "actions",
      cell: actionsCell,
    }),
  ];

  const table = useReactTable({
    data: children ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
  });

  const isLoading = children === undefined;
  const isEmpty = table.getRowModel().rows.length === 0;

  const tableRef = useRef<HTMLTableElement>(null);
  const { onKeyDown } = useTableKeyboardNavigation({
    table,
    tableRef,
  });

  const getContent = () => {
    if (isLoading) {
      return (
        <div className="c__datagrid__loader">
          <div className="c__datagrid__loader__background" />
          <Loader aria-label={tc("components.datagrid.loader_aria")} />
        </div>
      );
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
              const isSelected = !!selectedItemIds[row.original.id];
              return (
                <tr
                  key={row.original.id}
                  className={clsx("selectable", {
                    selected: isSelected,
                  })}
                  data-id={row.original.id}
                  tabIndex={0}
                  onClick={(e) => {
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

                          const newSelection = { ...selectedItemIds };
                          for (let i = startIndex; i <= endIndex; i++) {
                            newSelection[rows[i].original.id] = true;
                          }

                          setSelectedItemIds(newSelection);
                        }
                      } else if (e.metaKey || e.ctrlKey) {
                        setSelectedItemIds({
                          ...selectedItemIds,
                          [row.original.id]: !isSelected,
                        });
                        if (!isSelected) {
                          lastSelectedRowRef.current = row.id;
                        }
                      } else {
                        setSelectedItemIds({
                          [row.original.id]: true,
                        });
                        lastSelectedRowRef.current = row.id;
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
                  {row.getVisibleCells().map((cell, index, array) => (
                    <td
                      key={cell.id}
                      className={
                        index === array.length - 1
                          ? "c__datagrid__row__cell--actions"
                          : ""
                      }
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
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
      {renameItem && (
        <ExplorerRenameItemModal
          {...renameModal}
          item={renameItem}
          key={renameItem.id}
          onClose={() => {
            setRenameItem(undefined);
            renameModal.close();
          }}
        />
      )}
    </div>
  );
};

const ItemActions = ({
  item,
  onRename,
}: {
  item: Item;
  onRename: () => void;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  const deleteItems = useMutationDeleteItems();

  const handleDelete = async () => {
    addToast(
      <ToasterItem>
        <span className="material-icons">delete</span>
        <span>{t("explorer.actions.delete.toast", { count: 1 })}</span>
      </ToasterItem>
    );
    await deleteItems.mutateAsync([item.id]);
  };

  return (
    <>
      <DropdownMenu
        options={[
          {
            icon: <span className="material-icons">info</span>,
            label: t("explorer.grid.actions.info"),
            value: "info",
          },
          {
            icon: <span className="material-icons">group</span>,
            label: t("explorer.grid.actions.share"),
            callback: () => alert("Partager"),
          },
          {
            icon: <span className="material-icons">download</span>,
            label: t("explorer.grid.actions.download"),
            value: "download",
            showSeparator: true,
          },
          {
            icon: <span className="material-icons">edit</span>,
            label: t("explorer.grid.actions.rename"),
            value: "rename",
            callback: onRename,
            showSeparator: true,
          },
          {
            icon: <span className="material-icons">arrow_forward</span>,
            label: t("explorer.grid.actions.move"),
            value: "move",
          },
          {
            icon: <span className="material-icons">delete</span>,
            label: t("explorer.grid.actions.delete"),
            value: "delete",
            showSeparator: true,
            callback: handleDelete,
          },
        ]}
        isOpen={isOpen}
        onOpenChange={setIsOpen}
      >
        <Button
          onClick={() => setIsOpen(!isOpen)}
          color="primary-text"
          className="c__language-picker"
          icon={<span className="material-icons">more_horiz</span>}
        ></Button>
      </DropdownMenu>
    </>
  );
};

const ItemTitle = ({ item }: { item: Item }) => {
  const ref = useRef<HTMLSpanElement>(null);
  const [isOverflown, setIsOverflown] = useState(false);

  useEffect(() => {
    const checkOverflow = () => {
      const element = ref.current;
      // Should always be defined, but just in case.
      if (element) {
        setIsOverflown(element.scrollWidth > element.clientWidth);
      }
    };
    checkOverflow();

    window.addEventListener("resize", checkOverflow);
    return () => {
      window.removeEventListener("resize", checkOverflow);
    };
  }, [item.title]);

  const renderTitle = () => {
    // We need to have the element holding the ref nested because the Tooltip component
    // seems to make the top-most children ref null.
    return (
      <div style={{ display: "flex", overflow: "hidden" }}>
        <span className="explorer__grid__item__name__text" ref={ref}>
          {item.title}
        </span>
      </div>
    );
  };
  return (
    <div className="explorer__grid__item__name">
      <ItemIcon item={item} />
      {isOverflown ? (
        <Tooltip content={item.title}>{renderTitle()}</Tooltip>
      ) : (
        renderTitle()
      )}
    </div>
  );
};
