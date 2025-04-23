import { CellContext } from "@tanstack/react-table";
import { Item } from "@/features/drivers/types";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useMutationDeleteItems } from "../../hooks/useMutations";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { Button, useModal } from "@openfun/cunningham-react";
import { ExplorerRenameItemModal } from "../modals/ExplorerRenameItemModal";
import { useExplorer } from "../ExplorerContext";
import { useExplorerInner } from "../Explorer";
import { Draggable } from "../Draggable";

export type ExplorerGridActionsCellProps = CellContext<Item, unknown>;

export const ExplorerGridActionsCell = (
  params: ExplorerGridActionsCellProps
) => {
  const item = params.row.original;
  const { selectedItemsMap, setRightPanelForcedItem, setRightPanelOpen } =
    useExplorer();

  const { disableItemDragAndDrop } = useExplorerInner();
  const isSelected = !!selectedItemsMap[item.id];
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  const deleteItems = useMutationDeleteItems();
  const renameModal = useModal();

  const handleDelete = async () => {
    addToast(
      <ToasterItem>
        <span className="material-icons">delete</span>
        <span>{t("explorer.actions.delete.toast", { count: 1 })}</span>
      </ToasterItem>
    );
    await deleteItems.mutateAsync([item.id]);
  };

  const handleDownload = async () => {
    // Temporary solution, waiting for a proper download_url attribute.
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = item.url!;
    a.download = item.filename;
    document.body.appendChild(a);
    a.click();
  };

  return (
    <>
      <Draggable
        id={params.cell.id}
        item={item}
        className="explorer__grid__item__actions"
        disabled={disableItemDragAndDrop || !isSelected}
      >
        <DropdownMenu
          options={[
            {
              icon: <span className="material-icons">info</span>,
              label: t("explorer.grid.actions.info"),
              value: "info",
              callback: () => {
                setRightPanelForcedItem(item);
                setRightPanelOpen(true);
              },
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
              callback: handleDownload,
            },
            {
              icon: <span className="material-icons">edit</span>,
              label: t("explorer.grid.actions.rename"),
              value: "rename",
              callback: renameModal.open,
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
            className="explorer__grid__item__actions__button"
            icon={<span className="material-icons">more_horiz</span>}
          />
        </DropdownMenu>
        {renameModal.isOpen && (
          <ExplorerRenameItemModal {...renameModal} item={item} key={item.id} />
        )}
      </Draggable>
    </>
  );
};
