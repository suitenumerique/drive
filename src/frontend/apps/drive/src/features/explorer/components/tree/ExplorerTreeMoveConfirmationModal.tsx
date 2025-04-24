import { Item } from "@/features/drivers/types";
import { Button, Modal, ModalSize } from "@openfun/cunningham-react";
import { Trans, useTranslation } from "react-i18next";

export type ConfirmationMoveState = {
  sourceItem: Item;
  targetItem: Item;
  moveCallback?: () => void;
};

type ExplorerTreeMoveConfirmationModalProps = {
  isOpen: boolean;
  onClose: () => void;
  sourceItem: Item;
  targetItem: Item;
  onMove: () => void;
  itemsCount?: number;
};

export const ExplorerTreeMoveConfirmationModal = ({
  isOpen,
  onClose,
  sourceItem,
  targetItem,
  itemsCount = 1,
  onMove,
}: ExplorerTreeMoveConfirmationModalProps) => {
  const { t } = useTranslation();
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size={ModalSize.MEDIUM}
      rightActions={
        <>
          <Button color="secondary" onClick={onClose}>
            {t("explorer.tree.workspace.move.confirmation_modal.cancel_button")}
          </Button>
          <Button color="danger" onClick={onMove}>
            {t(
              "explorer.tree.workspace.move.confirmation_modal.confirm_button"
            )}
          </Button>
        </>
      }
      title={t("explorer.tree.workspace.move.confirmation_modal.title")}
    >
      <div>
        <p>
          <Trans
            i18nKey={
              itemsCount > 1
                ? "explorer.tree.workspace.move.confirmation_modal.description_multiple"
                : "explorer.tree.workspace.move.confirmation_modal.description"
            }
            values={{
              count: itemsCount,
              sourceItem: sourceItem.title,
              targetItem: targetItem.title,
            }}
          />
        </p>
      </div>
    </Modal>
  );
};
