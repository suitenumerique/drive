import { getDriver } from "@/features/config/Config";
import { Item, ItemType } from "@/features/drivers/types";
import { Button, Modal, ModalSize, useModal } from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { ExplorerGridItemsList } from "../../grid/ExplorerGrid";
import { useEffect, useMemo, useRef, useState } from "react";
// import workspaceLogo from "@/assets/workspace_logo.svg";
import { NavigationEvent } from "../../ExplorerContext";
import {
  HorizontalSeparator,
  useResponsive,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import {
  BreadcrumbItem,
  Breadcrumbs,
} from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { Trans, useTranslation } from "react-i18next";
import clsx from "clsx";
import { useMoveItems } from "@/features/explorer/api/useMoveItem";
import { addItemsMovedToast } from "../../toasts/addItemsMovedToast";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { ExplorerItemIcon } from "../../ExplorerFolderIcon";
import { ExplorerTreeMoveConfirmationModal } from "../../tree/ExplorerTreeMoveConfirmationModal";

interface ExplorerMoveFolderProps {
  isOpen: boolean;
  onClose: () => void;
  initialFolderId?: string;
  itemsToMove: Item[];
}

export const ExplorerMoveFolder = ({
  isOpen,
  onClose,
  initialFolderId,
  itemsToMove,
}: ExplorerMoveFolderProps) => {
  const { isDesktop } = useResponsive();
  const { t } = useTranslation();
  const treeContext = useTreeContext<Item>();
  const isInitRef = useRef(false);
  const [itemId, setItemId] = useState<string | null>(initialFolderId ?? null);
  const [history, setHistory] = useState<Item[]>([]);
  const moveItems = useMoveItems();
  const [selectedItems, setSelectedItems] = useState<Item[]>([]);
  const moveConfirmationModal = useModal();
  // Update history when navigating
  const onNavigate = (event: NavigationEvent) => {
    const item = event.item as Item;
    setSelectedItems([]);
    setItemId(item.id);
    setHistory((prev) => [...prev, item]);
  };

  // Add a function to go back in history
  const goBackToItem = (item: Item) => {
    setItemId(item.id);
    setHistory((prev) => prev.slice(0, prev.indexOf(item) + 1));
  };

  const getBreadcrumbsItems = () => {
    const breadcrumbsItems: BreadcrumbItem[] = [
      {
        content: (
          <div
            className="c__breadcrumbs__button"
            onClick={() => {
              setItemId(null);
              setHistory([]);
            }}
          >
            Espaces
          </div>
        ),
      },
    ];

    let breadcrumbsData = history;
    if (initialFolderId && !isInitRef.current) {
      breadcrumbsData =
        (treeContext?.treeData.getAncestors(initialFolderId) as Item[]) ?? [];
      setHistory(breadcrumbsData);
      isInitRef.current = true;
    }

    breadcrumbsData.forEach((item, index) => {
      const isWorkspace = itemIsWorkspace(item) || item.main_workspace;

      breadcrumbsItems.push({
        content: (
          <button
            className="c__breadcrumbs__button"
            onClick={() => goBackToItem(item)}
          >
            {isWorkspace && <ExplorerItemIcon item={item} size={24} />}
            {item.main_workspace
              ? t("explorer.workspaces.mainWorkspace")
              : item.title}
          </button>
        ),
      });
    });

    return breadcrumbsItems;
  };

  const breadcrumbsItems = useMemo(() => {
    return getBreadcrumbsItems();
  }, [history, initialFolderId]);

  const { data: firstLevelItems } = useQuery({
    queryKey: ["firstLevelItems"],
    queryFn: () => getDriver().getItems(),
  });

  const { data: item } = useQuery({
    queryKey: ["item", itemId],
    queryFn: () => getDriver().getItem(itemId!),
    enabled: itemId !== null,
  });

  const { data: itemChildren } = useQuery({
    queryKey: ["items", itemId, "children", []],
    enabled: itemId !== null,
    queryFn: () => {
      if (itemId === null) {
        return Promise.resolve(undefined);
      }
      return getDriver().getChildren(itemId, { type: ItemType.FOLDER });
    },
  });

  const items = useMemo(() => {
    let items = [];
    if (itemId === null) {
      items = firstLevelItems ?? [];
    } else {
      items = itemChildren ?? [];
    }

    // Filter out the itemToMove from the items list

    items = items
      .filter((item) => !itemsToMove.some((i) => i.id === item.id))
      .sort((a, b) => {
        // Always put main_workspace first
        if (a.main_workspace) return -1;
        if (b.main_workspace) return 1;

        // Then sort other items by name
        return a.title.localeCompare(b.title, undefined, {
          sensitivity: "base",
        });
      })
      .map((item) => {
        if (item.main_workspace) {
          return {
            ...item,
            title: t("explorer.workspaces.mainWorkspace"),
          };
        }
        return item;
      });

    console.log("items", items);
    return items;
  }, [itemId, firstLevelItems, itemChildren]);

  useEffect(() => {
    if (initialFolderId) {
      setItemId(initialFolderId);
    }
  }, [initialFolderId]);

  const onCloseModal = () => {
    onClose();
    setSelectedItems([]);
    setItemId(null);
    setHistory([]);
    isInitRef.current = false;
  };

  const selectedItemsMap = useMemo(() => {
    return selectedItems.reduce((acc, item) => {
      acc[item.id] = item;
      return acc;
    }, {} as Record<string, Item>);
  }, [selectedItems]);

  const getMoveData = () => {
    const ids = itemsToMove.map((item) => item.id);
    const pathSegments = itemsToMove[0].path.split(".");
    const oldParentId = pathSegments[pathSegments.length - 2];
    const oldRootParentId = pathSegments[0];
    const newParentId =
      selectedItems.length === 1 ? selectedItems[0].id : itemId!;
    const newParentItem = selectedItems.length === 1 ? selectedItems[0] : item;

    const newRootId = newParentItem?.path.split(".")[0];
    return {
      ids,
      oldParentId,
      oldRootParentId,
      newParentId,
      newRootId,
    };
  };
  const handleMove = (
    ids: string[],
    newParentId: string,
    oldParentId: string
  ) => {
    moveItems.mutateAsync(
      {
        ids: ids,
        parentId: newParentId,
        oldParentId: oldParentId,
      },
      {
        onSuccess: () => {
          onCloseModal();
          addItemsMovedToast(ids.length);
        },
      }
    );
  };

  const onMove = () => {
    const isRoot = breadcrumbsItems.length === 1;
    if (
      (!itemId && !isRoot) ||
      (itemId === null && selectedItems.length === 0)
    ) {
      return;
    }

    if (itemId && item === undefined) {
      return;
    }
    const data = getMoveData();
    if (data.newRootId !== data.oldRootParentId) {
      moveConfirmationModal.open();
      return;
    }

    handleMove(data.ids, data.newParentId, data.oldParentId);
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        closeOnClickOutside
        title={
          <div className="modal__move__header">
            <span className="modal__move__title">Déplacer</span>
            <span className="modal__move__description">
              <Trans
                i18nKey={
                  itemsToMove.length === 1
                    ? "explorer.modal.move.description_one_item"
                    : "explorer.modal.move.description_multiple_items"
                }
                values={{
                  count: itemsToMove.length,
                  name: itemsToMove[0].title,
                }}
              />
            </span>
          </div>
        }
        onClose={onCloseModal}
        size={isDesktop ? ModalSize.LARGE : ModalSize.FULL}
        rightActions={
          <div className="modal__move__footer">
            <Button color="secondary" onClick={onCloseModal}>
              {t("common.cancel")}
            </Button>
            <Button
              color="primary"
              disabled={!itemId && selectedItems.length === 0}
              onClick={onMove}
            >
              {t("explorer.modal.move.move_button")}
            </Button>
          </div>
        }
      >
        <div className="noPadding">
          <div className="modal__move">
            <HorizontalSeparator />
          </div>
          <div
            className="modal__move__content"
            style={{ height: isDesktop ? "300px" : "100%" }}
          >
            <div
              className="modal__move__content__container"
              onClick={(e) => {
                const target = e.target as HTMLElement;
                const isList = target.closest(".c__datagrid__table__container");
                const isBreadcrumb = target.closest(
                  ".modal__move__breadcrumbs"
                );
                if (isList || isBreadcrumb) {
                  return;
                }
                setSelectedItems([]);
              }}
            >
              <div className="modal__move__breadcrumbs">
                <Breadcrumbs items={breadcrumbsItems} />
              </div>
              <div
                className={clsx(
                  "c__datagrid explorer__grid explorer__compact",
                  {
                    modal__move__empty: items.length === 0,
                  }
                )}
              >
                {items.length > 0 ? (
                  <ExplorerGridItemsList
                    isCompact
                    items={items}
                    gridActionsCell={() => <div />}
                    onNavigate={onNavigate}
                    selectedItems={selectedItems}
                    setSelectedItems={setSelectedItems}
                    selectedItemsMap={selectedItemsMap}
                  />
                ) : (
                  <div className="modal__move__empty">
                    <span>{t("explorer.modal.move.empty_folder")}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <HorizontalSeparator />
        </div>
      </Modal>
      {moveConfirmationModal.isOpen && (
        <ExplorerTreeMoveConfirmationModal
          itemsCount={selectedItems.length}
          isOpen={moveConfirmationModal.isOpen}
          onClose={() => {
            moveConfirmationModal.close();
          }}
          sourceItem={itemsToMove[0]}
          targetItem={selectedItems.length === 1 ? selectedItems[0] : item!}
          onMove={() => {
            handleMove(
              getMoveData().ids,
              getMoveData().newParentId,
              getMoveData().oldParentId
            );
            moveConfirmationModal.close();
          }}
        />
      )}
    </>
  );
};
