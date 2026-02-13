import { Item, ItemType, Role } from "@/features/drivers/types";
import {
  Button,
  Modal,
  ModalSize,
  useModal,
} from "@gouvfr-lasuite/cunningham-react";
import { useQueryClient } from "@tanstack/react-query";
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
  EmbeddedExplorer,
  useEmbeddedExplorer,
} from "@/features/explorer/components/embedded-explorer/EmbeddedExplorer";
import { AddFolderButton } from "./AddFolderButton";
import { useGlobalExplorer } from "../../GlobalExplorerContext";
import { useRef } from "react";
import { useItem } from "@/features/explorer/hooks/useQueries";

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
  const isMoveToRoot = useRef(false);
  const { itemId: currentItemId } = useGlobalExplorer();
  const queryClient = useQueryClient();

  const { t } = useTranslation();
  const treeContext = useTreeContext<Item>();
  const moveItems = useMoveItems();

  const imOwner = itemsToMove.every((item) => {
    return item.user_role === Role.OWNER;
  });

  const showMoveToRootButton =
    imOwner && itemsToMove.every((item) => item.path.split(".").length > 1);

  const itemsExplorer = useEmbeddedExplorer({
    initialFolderId: initialFolderId,
    isCompact: true,
    gridProps: {
      enableMetaKeySelection: false,
      gridActionsCell: () => <div />,
      disableKeyboardNavigation: true,
    },
    itemsFilters: {
      type: ItemType.FOLDER,
    },
    itemsFilter: (items) => {
      const filteredItems = items.filter((itemFiltered) => {
        return !itemsToMove.some((i) => {
          return i.id === itemFiltered.id;
        });
      });

      return filteredItems;
    },
    breadcrumbsRight: () => (
      <Button
        size="small"
        variant="tertiary"
        icon={<AddFolderButton />}
        onClick={createFolderModal.open}
      />
    ),
  });

  const moveConfirmationModal = useModal();
  const createFolderModal = useModal();

  const { data: item } = useItem(itemsExplorer.currentItemId!, {
    enabled: !!itemsExplorer.currentItemId,
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
        : (itemsExplorer.currentItemId ?? undefined);
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
    newParentId: string | undefined,
    oldParentId: string,
  ) => {
    moveItems.mutateAsync(
      {
        ids: ids,
        parentId: newParentId,
        oldParentId: oldParentId,
      },

      {
        onSettled() {
          isMoveToRoot.current = false;
        },
        onSuccess: () => {
          onCloseModal();
          addItemsMovedToast(ids.length);

          if (newParentId) {
            // update the tree
            let childrenCount =
              treeContext?.treeData.getNode(newParentId)?.children?.length ?? 0;

            ids.forEach((id) => {
              treeContext?.treeData.moveNode(id, newParentId, childrenCount);
              childrenCount++;
            });
          }

          // If the current item is moved, we invalidate the item and breadcrumb queries
          if (ids.includes(currentItemId)) {
            queryClient.invalidateQueries({
              queryKey: ["items", currentItemId],
            });
            queryClient.invalidateQueries({
              queryKey: ["breadcrumb", currentItemId],
            });
          }
        },
      },
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

  const onMoveToRoot = () => {
    isMoveToRoot.current = true;
    moveConfirmationModal.open();
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        aria-label={t("explorer.modal.move.aria_label")}
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
        size={isDesktop ? ModalSize.MEDIUM : ModalSize.FULL}
        leftActions={
          <>
            {showMoveToRootButton && (
              <Button
                variant="tertiary"
                onClick={onMoveToRoot}
                className="move-to-root-button"
                fullWidth={true}
              >
                {t("explorer.modal.move.move_to_root")}
              </Button>
            )}
          </>
        }
        rightActions={
          <>
            <Button variant="tertiary" onClick={onCloseModal} fullWidth={true}>
              {t("common.cancel")}
            </Button>
            <Button
              disabled={
                !itemsExplorer.currentItemId &&
                itemsExplorer.selectedItems.length === 0
              }
              onClick={onMove}
              fullWidth={true}
            >
              {t("explorer.modal.move.move_button")}
            </Button>
          </>
        }
      >
        <div className="noPadding">
          <HorizontalSeparator withPadding={false} />
          <div className="modal__move__explorer">
            <EmbeddedExplorer {...itemsExplorer} showSearch={true} />
          </div>
          <HorizontalSeparator withPadding={false} />
        </div>
      </Modal>
      {createFolderModal.isOpen && (
        <ExplorerCreateFolderModal
          {...createFolderModal}
          parentId={itemsExplorer.currentItemId ?? undefined}
        />
      )}
      {moveConfirmationModal.isOpen && (
        <ExplorerTreeMoveConfirmationModal
          itemsCount={itemsToMove.length}
          isMoveToRoot={isMoveToRoot.current}
          isOpen={moveConfirmationModal.isOpen}
          onClose={() => {
            moveConfirmationModal.close();
            isMoveToRoot.current = false;
          }}
          sourceItem={itemsToMove[0]}
          targetItem={
            itemsExplorer.selectedItems.length === 1
              ? itemsExplorer.selectedItems[0]
              : item!
          }
          onMove={() => {
            const data = getMoveData();

            if (isMoveToRoot.current) {
              handleMove(data.ids, undefined, data.oldParentId);
            } else {
              handleMove(data.ids, data.newParentId, data.oldParentId);
            }
            isMoveToRoot.current = false;
            moveConfirmationModal.close();
          }}
        />
      )}
    </>
  );
};
