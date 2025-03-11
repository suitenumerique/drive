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
import { database } from "./database";
import { FolderIcon } from "@/features/ui/components/icon/Icon";
import { FileIcon } from "@/features/ui/components/icon/Icon";
import clsx from "clsx";
import { useRouter } from "next/router";
import { DropdownMenu } from "@lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";

export const ExplorerGrid = () => {
  const { t } = useTranslation();
  const lastSelectedRowRef = useRef<string | null>(null);
  const columnHelper = createColumnHelper<Item>();
  const {
    setSelectedItemIds: setSelectedItems,
    selectedItemIds: selectedItems,
    onNavigate,
  } = useExplorer();
  const router = useRouter();
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
    columnHelper.accessor("lastUpdate", {
      header: t("explorer.grid.last_update"),
      cell: (info) => (
        <div className="explorer__grid__item__last-update">
          {info.row.original.lastUpdate}
        </div>
      ),
    }),
    columnHelper.display({
      id: "actions",
      cell: () => <ItemActions />,
    }),
  ];

  const table = useReactTable({
    data: database,
    columns,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
    state: {
      rowSelection: selectedItems,
    },
  });

  return (
    <div className="c__datagrid explorer__grid">
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
