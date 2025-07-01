import { getDriver } from "@/features/config/Config";
import { Item, ItemType } from "@/features/drivers/types";
import { Button, Modal, ModalSize, useModal } from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import {
  HorizontalSeparator,
  useResponsive,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { Trans, useTranslation } from "react-i18next";
import { useMoveItems } from "@/features/explorer/api/useMoveItem";
import { addItemsMovedToast } from "../../toasts/addItemsMovedToast";
import { ExplorerTreeMoveConfirmationModal } from "../../tree/ExplorerTreeMoveConfirmationModal";
import { ExplorerCreateFolderModal } from "../ExplorerCreateFolderModal";
import {
  ExplorerGridItemsExplorer,
  useExplorerGridItemsExplorer,
} from "../../grid/ExplorerGridItemsExplorer";
import add_folder from "@/assets/icons/folder-tiny-plus.svg";

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
  const moveItems = useMoveItems();

  const itemsExplorer = useExplorerGridItemsExplorer({
    initialFolderId: initialFolderId,
    isCompact: true,
    gridProps: {
      enableMetaKeySelection: false,
      gridActionsCell: () => <div />,
    },
    itemsFilters: {
      type: ItemType.FOLDER,
    },
    itemsFilter: (items) => {
      return items.filter(
        (itemFiltered) =>
          !itemsToMove.some((i) => {
            return i.id === itemFiltered.id;
          })
      );
    },
    breadcrumbsRight: () =>
      itemsExplorer.currentItemId ? (
        <Button
          size="small"
          color="primary-text"
          onClick={createFolderModal.open}
        >
          <img src={add_folder.src} alt="add" />
        </Button>
      ) : null,
  });

  const moveConfirmationModal = useModal();
  const createFolderModal = useModal();

  const { data: item } = useQuery({
    queryKey: ["item", itemsExplorer.currentItemId],
    queryFn: () => getDriver().getItem(itemsExplorer.currentItemId!),
    enabled: itemsExplorer.currentItemId !== null,
  });

  const onCloseModal = () => {
    onClose();
    itemsExplorer.setSelectedItems([]);
  };

  const getMoveData = () => {
    const ids = itemsToMove.map((item) => item.id);
    const pathSegments = itemsToMove[0].path.split(".");
    const oldParentId = pathSegments[pathSegments.length - 2];
    const oldRootParentId = pathSegments[0];
    const newParentId =
      itemsExplorer.selectedItems.length === 1
        ? itemsExplorer.selectedItems[0].id
        : itemsExplorer.currentItemId!;
    const newParentItem =
      itemsExplorer.selectedItems.length === 1
        ? itemsExplorer.selectedItems[0]
        : item;

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
    if (
      itemsExplorer.currentItemId === null &&
      itemsExplorer.selectedItems.length === 0
    ) {
      return;
    }

    // If we are in a folder, and the item is not found, we can't move
    if (itemsExplorer.currentItemId && item === undefined) {
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
              disabled={
                !itemsExplorer.currentItemId &&
                itemsExplorer.selectedItems.length === 0
              }
              onClick={onMove}
            >
              {t("explorer.modal.move.move_button")}
            </Button>
          </div>
        }
      >
        <div className="noPadding">
          <HorizontalSeparator />
          <div className="modal__move__explorer">
            <ExplorerGridItemsExplorer {...itemsExplorer} />
          </div>
          <HorizontalSeparator />
        </div>
      </Modal>
      {createFolderModal.isOpen && itemsExplorer.currentItemId && (
        <ExplorerCreateFolderModal
          {...createFolderModal}
          parentId={itemsExplorer.currentItemId}
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
          targetItem={
            itemsExplorer.selectedItems.length === 1
              ? itemsExplorer.selectedItems[0]
              : item!
          }
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
