import React, { useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Item, ItemType } from "@/features/drivers/types";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { useDeleteItem } from "@/features/explorer/hooks/useDeleteItem";
import { useModal } from "@openfun/cunningham-react";
import { ExplorerMoveFolder } from "@/features/explorer/components/modals/move/ExplorerMoveFolderModal";
import { ExplorerRenameItemModal } from "@/features/explorer/components/modals/ExplorerRenameItemModal";
import { WorkspaceShareModal } from "@/features/explorer/components/modals/share/WorkspaceShareModal";
import { FileShareModal } from "@/features/explorer/components/modals/share/FileShareModal";
import { itemIsWorkspace } from "@/features/drivers/utils";
import {
  NavigationEvent,
  NavigationEventType,
} from "@/features/explorer/components/GlobalExplorerContext";
import clsx from "clsx";

export type EmbeddedExplorerContextMenuProps = {
  item: Item;
  parentItem?: Item;
  onNavigate?: (event: NavigationEvent) => void;
  setRightPanelForcedItem?: (item: Item | undefined) => void;
  setRightPanelOpen?: (open: boolean) => void;
  position: { x: number; y: number };
  onClose: () => void;
};

export const EmbeddedExplorerContextMenu = ({
  item,
  parentItem,
  onNavigate,
  setRightPanelForcedItem,
  setRightPanelOpen,
  position,
  onClose,
}: EmbeddedExplorerContextMenuProps) => {
  const { t } = useTranslation();
  const { handleDownloadItem } = useDownloadItem();
  const { deleteItems } = useDeleteItem();

  const moveModal = useModal();
  const renameModal = useModal();
  const shareWorkspaceModal = useModal();
  const shareFileModal = useModal();
  const menuRef = useRef<HTMLDivElement>(null);

  const isWorkspace = itemIsWorkspace(item);
  const canShareWorkspace = isWorkspace && item.abilities.accesses_manage;
  const canShareFile = !isWorkspace && item.abilities.accesses_manage;

  // Close menu when clicking outside and adjust position based on available space
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    // Adjust menu position based on available space
    const adjustMenuPosition = () => {
      if (!menuRef.current) return;

      const menu = menuRef.current;
      const menuRect = menu.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      // Reset any previous adjustments
      menu.style.left = `${position.x}px`;
      menu.style.top = `${position.y}px`;
      menu.style.transform = "none";

      // Check if menu goes beyond right edge
      if (position.x + menuRect.width > viewportWidth) {
        menu.style.left = `${position.x - menuRect.width}px`;
      }

      // Check if menu goes beyond bottom edge
      if (position.y + menuRect.height > viewportHeight) {
        menu.style.top = `${position.y - menuRect.height}px`;
      }

      // Final check: if still out of bounds, adjust to stay within viewport
      const finalRect = menu.getBoundingClientRect();
      if (finalRect.right > viewportWidth) {
        menu.style.left = `${viewportWidth - finalRect.width - 10}px`;
      }
      if (finalRect.bottom > viewportHeight) {
        menu.style.top = `${viewportHeight - finalRect.height - 10}px`;
      }
      if (finalRect.left < 0) {
        menu.style.left = "10px";
      }
      if (finalRect.top < 0) {
        menu.style.top = "10px";
      }
    };

    // Adjust position after menu is rendered
    const timeoutId = setTimeout(adjustMenuPosition, 0);

    // Also adjust position on window resize
    const handleResize = () => {
      adjustMenuPosition();
    };

    document.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("resize", handleResize);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("resize", handleResize);
      clearTimeout(timeoutId);
    };
  }, [onClose, position]);

  const handleDownload = () => {
    handleDownloadItem(item);
    onClose();
  };

  const handleMove = () => {
    moveModal.open();
    onClose();
  };

  const handleRename = () => {
    renameModal.open();
    onClose();
  };

  const handleDelete = async () => {
    await deleteItems([item.id]);
    onClose();
  };

  const handleInfo = () => {
    setRightPanelForcedItem?.(item);
    setRightPanelOpen?.(true);
    onClose();
  };

  const handleOpen = () => {
    if (item.type === ItemType.FOLDER) {
      onNavigate?.({
        type: NavigationEventType.ITEM,
        item: item,
      });
    }
    onClose();
  };

  const handleShareWorkspace = () => {
    shareWorkspaceModal.open();
    onClose();
  };

  const handleShareFile = () => {
    shareFileModal.open();
    onClose();
  };

  const menuItems = [
    {
      icon: <span className="material-icons">open_in_new</span>,
      label: t("explorer.grid.actions.open"),
      onClick: handleOpen,
      hidden: item.type !== ItemType.FOLDER,
    },
    {
      icon: <span className="material-icons">info</span>,
      label: t("explorer.grid.actions.info"),
      onClick: handleInfo,
    },
    {
      icon: <span className="material-icons">group</span>,
      label: item.abilities.accesses_manage
        ? t("explorer.tree.workspace.options.share")
        : t("explorer.tree.workspace.options.share_view"),
      onClick: handleShareWorkspace,
      hidden: !canShareWorkspace,
    },
    {
      icon: <span className="material-icons">group</span>,
      label: item.abilities.accesses_manage
        ? t("explorer.tree.workspace.options.share")
        : t("explorer.tree.workspace.options.share_view"),
      onClick: handleShareFile,
      hidden: !canShareFile,
    },
    {
      icon: <span className="material-icons">arrow_forward</span>,
      label: t("explorer.grid.actions.move"),
      onClick: handleMove,
      hidden: !item.abilities.move,
    },
    {
      icon: <span className="material-icons">edit</span>,
      label: t("explorer.grid.actions.rename"),
      onClick: handleRename,
      hidden: !item.abilities.update,
    },
    {
      icon: <span className="material-icons">download</span>,
      label: t("explorer.grid.actions.download"),
      onClick: handleDownload,
      hidden: item.type === ItemType.FOLDER,
      separator: true,
    },
    {
      icon: <span className="material-icons">delete</span>,
      label: !isWorkspace
        ? t("explorer.tree.workspace.options.delete_folder")
        : t("explorer.tree.workspace.options.delete_workspace"),
      onClick: handleDelete,
      hidden: !item.abilities.destroy || item.main_workspace,
    },
  ].filter((item) => !item.hidden);

  return (
    <>
      <div
        ref={menuRef}
        className="embedded-explorer-context-menu"
        style={{
          position: "fixed",
          left: position.x,
          top: position.y,
          zIndex: 1000,
          backgroundColor: "white",
          border: "1px solid #ccc",
          borderRadius: "4px",
          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
          minWidth: "200px",
        }}
      >
        {menuItems.map((menuItem, index) => (
          <React.Fragment key={index}>
            {menuItem.separator && index > 0 && (
              <div
                style={{
                  height: "1px",
                  backgroundColor: "#eee",
                  margin: "4px 0",
                }}
              />
            )}
            <button
              className={clsx("context-menu-item")}
              onClick={menuItem.onClick}
              style={{
                width: "100%",
                padding: "8px 16px",
                border: "none",
                backgroundColor: "transparent",
                textAlign: "left",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#f5f5f5";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "transparent";
              }}
            >
              {menuItem.icon}
              <span>{menuItem.label}</span>
            </button>
          </React.Fragment>
        ))}
      </div>

      {/* Modals */}
      {moveModal.isOpen && (
        <ExplorerMoveFolder
          {...moveModal}
          onClose={moveModal.close}
          itemsToMove={[item]}
          initialFolderId={parentItem?.id}
        />
      )}

      {renameModal.isOpen && (
        <ExplorerRenameItemModal
          {...renameModal}
          item={item}
          onClose={renameModal.close}
        />
      )}

      {shareWorkspaceModal.isOpen && (
        <WorkspaceShareModal {...shareWorkspaceModal} item={item} />
      )}

      {shareFileModal.isOpen && (
        <FileShareModal {...shareFileModal} item={item} />
      )}
    </>
  );
};
