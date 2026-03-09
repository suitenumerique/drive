import { Button } from "@gouvfr-lasuite/cunningham-react";

import { Modal, ModalProps, ModalSize } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";

export const CancelUploadConfirmationModal = ({
  onConfirm,
  ...props
}: Pick<ModalProps, "isOpen" | "onClose"> & {
  onConfirm: () => void;
}) => {
  const { t } = useTranslation();
  return (
    <Modal
      title={t("explorer.actions.upload.cancel_modal.title")}
      size={ModalSize.MEDIUM}
      rightActions={
        <>
          <Button
            variant="bordered"
            onClick={() => {
              props.onClose();
            }}
          >
            {t("explorer.actions.upload.cancel_modal.keep")}
          </Button>
          <Button
            color="error"
            onClick={() => {
              onConfirm();
              props.onClose();
            }}
          >
            {t("explorer.actions.upload.cancel_modal.confirm")}
          </Button>
        </>
      }
      {...props}
    >
      <div className="c__modal__content__text">
        {t("explorer.actions.upload.cancel_modal.description")}
      </div>
    </Modal>
  );
};
