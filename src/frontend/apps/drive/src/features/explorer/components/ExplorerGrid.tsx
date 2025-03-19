import { ItemType } from "@/features/drivers/types";
import { Item } from "@/features/drivers/types";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { FolderIcon } from "@/features/ui/components/icon/Icon";
import { FileIcon } from "@/features/ui/components/icon/Icon";
import clsx from "clsx";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { Button, Loader, useCunningham } from "@openfun/cunningham-react";
import gridEmpty from "@/assets/grid_empty.png";

export const ExplorerGrid = () => {
  const { t } = useTranslation();
  const { t: tc } = useCunningham();
  const lastSelectedRowRef = useRef<string | null>(null);
  const columnHelper = createColumnHelper<Item>();
  const {
    setSelectedItemIds: setSelectedItems,
    selectedItemIds: selectedItems,
    onNavigate,
    children,
  } = useExplorer();
  const columns = [
    columnHelper.accessor("title", {
      header: t("explorer.grid.name"),
      cell: (params) => (
        <div className="explorer__grid__item__name">
          {params.row.original.type === ItemType.FOLDER && <FolderIcon />}
          {params.row.original.type === ItemType.FILE && <FileIcon />}
          <span className="explorer__grid__item__name__text">
            {params.row.original.title}
          </span>
        </div>
      ),
    }),
    columnHelper.accessor("updated_at", {
      header: t("explorer.grid.last_update"),
      cell: (info) => (
        <div className="explorer__grid__item__last-update">
          {info.row.original.updated_at.toDateString()}
        </div>
      ),
    }),
    columnHelper.display({
      id: "actions",
      cell: () => <ItemActions />,
    }),
  ];

  const table = useReactTable({
    data: children ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
    state: {
      rowSelection: selectedItems,
    },
  });

  const isLoading = children === undefined;
  const isEmpty = table.getRowModel().rows.length === 0;

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
        <table>
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
              const isSelected = !!selectedItems[row.original.id];
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

                          const newSelection = { ...selectedItems };
                          for (let i = startIndex; i <= endIndex; i++) {
                            newSelection[rows[i].original.id] = true;
                          }

                          setSelectedItems(newSelection);
                        }
                      } else if (e.metaKey || e.ctrlKey) {
                        setSelectedItems({
                          ...selectedItems,
                          [row.original.id]: !isSelected,
                        });
                        if (!isSelected) {
                          lastSelectedRowRef.current = row.id;
                        }
                      } else {
                        setSelectedItems({
                          [row.original.id]: true,
                        });
                        lastSelectedRowRef.current = row.id;
                      }
                    }

                    // Double click to open the item
                    if (e.detail === 2) {
                      onNavigate({
                        type: NavigationEventType.ITEM,
                        item: row.original,
                      });
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
    </div>
  );
};

const ItemActions = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  return (
    <DropdownMenu
      options={[
        {
          icon: <span className="material-icons">info</span>,
          label: "Informations",
          value: "info",
        },
        {
          icon: <span className="material-icons">group</span>,
          label: "Partager",
          callback: () => alert("Partager"),
        },
        {
          icon: <span className="material-icons">download</span>,
          label: "Télécharger",
          value: "download",

          showSeparator: true,
        },
        {
          icon: <span className="material-icons">edit</span>,
          label: "Renommer",
          value: "rename",

          showSeparator: true,
        },
        {
          icon: <span className="material-icons">arrow_forward</span>,
          label: "Déplacer",
          value: "move",
        },
        {
          icon: <span className="material-icons">arrow_back</span>,
          label: "Dupliquer",
          value: "duplicate",
        },
        {
          icon: <span className="material-icons">add</span>,
          isDisabled: true,
          label: "Crééer un raccourci",
          value: "create-shortcut",
          showSeparator: true,
        },
        {
          icon: <span className="material-icons">delete</span>,
          label: "Supprimer",
          value: "delete",
          showSeparator: true,
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
  );
};
