import { CellContext } from "@tanstack/react-table";
import { Item, ItemType } from "@/features/drivers/types";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useMutationDeleteItems } from "@/features/explorer/hooks/useMutations";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { Button, useModal } from "@openfun/cunningham-react";
import { ExplorerRenameItemModal } from "@/features/explorer/components/modals/ExplorerRenameItemModal";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import { Draggable } from "@/features/explorer/components/Draggable";
import { WorkspaceShareModal } from "@/features/explorer/components/modals/share/WorkspaceShareModal";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { useEmbeddedExplorerGirdContext } from "./EmbeddedExplorerGrid";
import { FileShareModal } from "@/features/explorer/components/modals/share/FileShareModal";
import { useDisableDragGridItem } from "./hooks";
import { downloadFile } from "@/features/items/utils";

export type EmbeddedExplorerGridActionsCellProps = CellContext<Item, unknown>;

export const EmbeddedExplorerGridActionsCell = (
  params: EmbeddedExplorerGridActionsCellProps
) => {
  const item = params.row.original;
  const { setRightPanelForcedItem, setRightPanelOpen } = useGlobalExplorer();
  const { openMoveModal, setMoveItem } = useEmbeddedExplorerGirdContext();
  const disableDrag = useDisableDragGridItem(item);
  const shareWorkspaceModal = useModal();
  const shareFileModal = useModal();

  const [isOpen, setIsOpen] = useState(false);
  const isWorkspace = itemIsWorkspace(item);
  const canShareWorkspace = isWorkspace;
  const canShareFile = item.type === ItemType.FILE;
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
    downloadFile(item.url!, item.filename);
  };

  const handleMove = () => {
    setMoveItem(item);
    openMoveModal();
  };

  return (
    <div
      onClick={(e) => {
        e.stopPropagation();
      }}
    >
      <Draggable
        id={params.cell.id}
        item={item}
        className="explorer__grid__item__actions"
        disabled={disableDrag}
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
              label: item.abilities.accesses_manage
                ? t("explorer.tree.workspace.options.share")
                : t("explorer.tree.workspace.options.share_view"),
              isHidden: !canShareWorkspace,
              callback: shareWorkspaceModal.open,
            },
            {
              icon: <span className="material-icons">group</span>,
              label: item.abilities.accesses_manage
                ? t("explorer.tree.workspace.options.share")
                : t("explorer.tree.workspace.options.share_view"),
              isHidden: !canShareFile,
              callback: shareFileModal.open,
            },
            {
              icon: <span className="material-icons">group</span>,
              label: t("explorer.grid.actions.move"),
              isHidden: !item.abilities.move,
              callback: handleMove,
            },
            {
              icon: <span className="material-icons">download</span>,
              label: t("explorer.grid.actions.download"),
              isHidden: item.type === ItemType.FOLDER,
              value: "download",
              showSeparator: true,
              callback: handleDownload,
            },
            {
              icon: <span className="material-icons">edit</span>,
              label: t("explorer.grid.actions.rename"),
              isHidden: !item.abilities.update,
              value: "rename",
              callback: renameModal.open,
              showSeparator: true,
            },
            {
              icon: <span className="material-icons">delete</span>,
              label: t("explorer.grid.actions.delete"),
              value: "delete",
              showSeparator: true,
              isHidden: !item.abilities.destroy,
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
        {canShareWorkspace && shareWorkspaceModal.isOpen && (
          <WorkspaceShareModal
            {...shareWorkspaceModal}
            item={item}
            key={item.id}
          />
        )}
        {canShareFile && shareFileModal.isOpen && (
          <FileShareModal {...shareFileModal} item={item} key={item.id} />
        )}
      </Draggable>
    </div>
  );
};
