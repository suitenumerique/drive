import { getDriver } from "@/features/config/Config";
import { Item, ItemType } from "@/features/drivers/types";
import { Button, Modal, ModalSize, useModal } from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { ExplorerGridItems } from "../../grid/ExplorerGridItems";
import { useEffect, useMemo, useState } from "react";
import add_folder from "@/assets/icons/folder-tiny-plus.svg";
import { NavigationEvent } from "../../ExplorerContext";
import {
  HorizontalSeparator,
  useResponsive,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { Trans, useTranslation } from "react-i18next";
import clsx from "clsx";
import { useMoveItems } from "@/features/explorer/api/useMoveItem";
import { addItemsMovedToast } from "../../toasts/addItemsMovedToast";
import { ExplorerTreeMoveConfirmationModal } from "../../tree/ExplorerTreeMoveConfirmationModal";
import { ExplorerCreateFolderModal } from "../ExplorerCreateFolderModal";
import {
  ExplorerGridBreadcrumbs,
  useBreadcrumbs,
} from "../../breadcrumbs/ExplorerGridBreadcrumbs";

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

  const [currentItemId, setCurrentItemId] = useState<string | null>(
    initialFolderId ?? null
  );
  const breadcrumbs = useBreadcrumbs({
    handleNavigate: (item) => {
      setCurrentItemId(item?.id ?? null);
    },
  });
  const treeContext = useTreeContext<Item>();

  const moveItems = useMoveItems();
  const [selectedItems, setSelectedItems] = useState<Item[]>([]);
  const moveConfirmationModal = useModal();
  const createFolderModal = useModal();

  // Update history when navigating
  const onNavigate = (event: NavigationEvent) => {
    const item = event.item as Item;
    setSelectedItems([]);
    breadcrumbs.update(item);
  };

  const { data: rootItems } = useQuery({
    queryKey: ["rootItems"],
    queryFn: () => getDriver().getItems(),
  });

  const { data: item } = useQuery({
    queryKey: ["item", currentItemId],
    queryFn: () => getDriver().getItem(currentItemId!),
    enabled: currentItemId !== null,
  });

  const { data: itemChildren } = useQuery({
    queryKey: ["items", currentItemId, "children", []],
    enabled: currentItemId !== null,
    queryFn: () => {
      if (currentItemId === null) {
        return Promise.resolve(undefined);
      }
      return getDriver().getChildren(currentItemId, { type: ItemType.FOLDER });
    },
  });

  const items = useMemo(() => {
    let items = [];
    // If no itemId, we are in the root, we explorer spaces
    if (currentItemId === null) {
      items = rootItems ?? [];
      // Sort items to put main_workspace first
      items = items.sort((a, b) => {
        if (a.main_workspace && !b.main_workspace) return -1;
        if (!a.main_workspace && b.main_workspace) return 1;
        return 0;
      });
    } else {
      items = itemChildren ?? [];
    }

    // Filter out the itemToMove from the items list
    items = items
      .filter(
        (itemFiltered) =>
          !itemsToMove.some((i) => {
            return i.id === itemFiltered.id;
          })
      )
      .map((item) => {
        if (item.main_workspace) {
          return {
            ...item,
            title: t("explorer.workspaces.mainWorkspace"),
          };
        }
        return item;
      });

    return items;
  }, [currentItemId, rootItems, itemChildren]);

  const onCloseModal = () => {
    onClose();
    setSelectedItems([]);
    breadcrumbs.resetAncestors();
  };

  const getMoveData = () => {
    const ids = itemsToMove.map((item) => item.id);
    const pathSegments = itemsToMove[0].path.split(".");
    const oldParentId = pathSegments[pathSegments.length - 2];
    const oldRootParentId = pathSegments[0];
    const newParentId =
      selectedItems.length === 1 ? selectedItems[0].id : currentItemId!;
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

          // update the tree
          let childrenCount =
            treeContext?.treeData.getNode(newParentId)?.children?.length ?? 0;

          ids.forEach((id) => {
            treeContext?.treeData.moveNode(id, newParentId, childrenCount);
            childrenCount++;
          });
        },
      }
    );
  };

  const onMove = () => {
    // If we are in the root, and no item is selected, we can't move
    if (currentItemId === null && selectedItems.length === 0) {
      return;
    }

    // If we are in a folder, and the item is not found, we can't move
    if (currentItemId && item === undefined) {
      return;
    }
    const data = getMoveData();
    if (data.newRootId !== data.oldRootParentId) {
      moveConfirmationModal.open();
      return;
    }

    handleMove(data.ids, data.newParentId, data.oldParentId);
  };

  // set the breadcrumbs to the initial folder
  useEffect(() => {
    if (initialFolderId) {
      const history =
        (treeContext?.treeData.getAncestors(initialFolderId) as Item[]) ?? [];
      breadcrumbs.resetAncestors(history);
    }
  }, [initialFolderId]);

  return (
    <>
      <Modal
        isOpen={isOpen}
        closeOnClickOutside
        title={
          <div className="modal__move__header">
            <span className="modal__move__title">
              {t("explorer.modal.move.title")}
            </span>
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
              disabled={!currentItemId && selectedItems.length === 0}
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
          <div className="modal__move__content">
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
                <ExplorerGridBreadcrumbs
                  {...breadcrumbs}
                  showSpacesItem={true}
                  buildWithTreeContext={false}
                />

                {currentItemId && (
                  <Button
                    size="small"
                    color="primary-text"
                    onClick={createFolderModal.open}
                  >
                    <img src={add_folder.src} alt="add" />
                  </Button>
                )}
              </div>
              <div
                className={clsx("explorer__grid ", {
                  modal__move__empty: items.length === 0,
                })}
              >
                {items.length > 0 ? (
                  <ExplorerGridItems
                    isCompact
                    enableMetaKeySelection={false}
                    items={items}
                    gridActionsCell={() => <div />}
                    onNavigate={onNavigate}
                    selectedItems={selectedItems}
                    setSelectedItems={setSelectedItems}
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
      {createFolderModal.isOpen && currentItemId && (
        <ExplorerCreateFolderModal
          {...createFolderModal}
          parentId={currentItemId}
        />
      )}
      {moveConfirmationModal.isOpen && (
        <ExplorerTreeMoveConfirmationModal
          itemsCount={itemsToMove.length}
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
