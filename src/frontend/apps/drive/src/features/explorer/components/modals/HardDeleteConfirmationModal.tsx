import { Button } from "@openfun/cunningham-react";

import {
  DecisionModalProps,
  Modal,
  ModalSize,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

export const HardDeleteConfirmationModal = ({
  onDecide,
  multiple = false,
  ...props
}: DecisionModalProps & {
  multiple?: boolean;
}) => {
  const { t } = useTranslation();
  return (
    <Modal
      title={t("explorer.trash.hard_delete.title")}
      size={ModalSize.MEDIUM}
      rightActions={
        <>
          <Button
            color="secondary"
            onClick={() => {
              onDecide(null);
              props.onClose();
            }}
          >
            {t("explorer.trash.hard_delete.cancel")}
          </Button>
          <Button
            color="danger"
            onClick={() => {
              onDecide("yes");
              props.onClose();
            }}
          >
            {t("explorer.trash.hard_delete.confirm")}
          </Button>
        </>
      }
      {...props}
    >
      <div className="c__modal__content__text">
        {t("explorer.trash.hard_delete.content", {
          count: multiple ? 2 : 1,
        })}
      </div>
    </Modal>
  );
};
