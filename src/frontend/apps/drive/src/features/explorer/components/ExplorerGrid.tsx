import { ItemType } from "@/features/drivers/types";
import { Item } from "@/features/drivers/types";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { FolderIcon } from "@/features/ui/components/icon/Icon";
import { FileIcon } from "@/features/ui/components/icon/Icon";
import clsx from "clsx";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import {
  Button,
  Loader,
  Tooltip,
  useCunningham,
} from "@openfun/cunningham-react";
import gridEmpty from "@/assets/grid_empty.png";
import { Draggable } from "./Draggable";
import { Droppable } from "./Droppable";
import { timeAgo } from "../utils/utils";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { addToast } from "@/features/ui/components/toaster/Toaster";

export const ExplorerGrid = () => {
  const { t } = useTranslation();
  const { t: tc } = useCunningham();
  const lastSelectedRowRef = useRef<string | null>(null);
  const columnHelper = createColumnHelper<Item>();
  const [overedItemIds, setOveredItemIds] = useState<Record<string, boolean>>(
    {}
  );
  const {
    setSelectedItemIds: setSelectedItems,
    selectedItemIds: selectedItems,
    onNavigate,
    children,
  } = useExplorer();

  const columns = [
    columnHelper.accessor("title", {
      header: t("explorer.grid.name"),
      cell: (params) => {
        const isSelected = !!selectedItems[params.row.original.id];

        return (
          <div className="explorer__grid__item__name">
            {params.row.original.type === ItemType.FOLDER && <FolderIcon />}
            {params.row.original.type === ItemType.FILE && <FileIcon />}

            {!isSelected && (
              <Draggable id={params.cell.id} item={params.row.original}>
                <span className="explorer__grid__item__name__text">
                  {params.row.original.title}
                </span>
              </Draggable>
            )}
            {isSelected && (
              <span className="explorer__grid__item__name__text">
                {params.row.original.title}
              </span>
            )}
          </div>
        );
      },
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
      cell: () => <ItemActions />,
    }),
  ];

  const dataTable = useMemo(() => {
    return (children ?? []).sort((a, b) => {
      // Trier d'abord par type (dossiers en premier)
      if (a.type !== b.type) {
        return a.type === ItemType.FOLDER ? -1 : 1;
      }
      // Ensuite trier par date de mise à jour (du plus récent au plus ancien)
      return b.updated_at.getTime() - a.updated_at.getTime();
    });
  }, [children]);

  const table = useReactTable({
    data: dataTable,
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
                            console.log("isOver", isOver, item.title);
                            setOveredItemIds((prev) => ({
                              ...prev,
                              [row.original.id]:
                                item.id === row.original.id ? false : isOver,
                            }));
                          }}
                        >
                          {(index > 0 || (index === 0 && isSelected)) && (
                            <Draggable
                              id={cell.id}
                              disabled={index === 0 ? false : !isSelected}
                              item={row.original}
                              style={{
                                width:
                                  index === 0 && !isSelected
                                    ? "fit-content"
                                    : "100%",
                              }}
                            >
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )}
                            </Draggable>
                          )}

                          {index === 0 && !isSelected && (
                            <>
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )}
                            </>
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
        size="medium"
        icon={<span className="material-icons">more_horiz</span>}
      ></Button>
    </DropdownMenu>
  );
};
