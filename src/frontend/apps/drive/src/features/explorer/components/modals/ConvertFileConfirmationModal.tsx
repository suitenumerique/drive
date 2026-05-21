import { Button } from "@gouvfr-lasuite/cunningham-react";

import {
  DecisionModalProps,
  Modal,
  ModalSize,
} from "@gouvfr-lasuite/cunningham-react";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";

export const ConvertFileConfirmationModal = ({
  onDecide,
  ...props
}: DecisionModalProps & {
  count?: number;
}) => {
  const { t } = useTranslation();
  return (
    <Modal
      title={t("explorer.convert.file.title")}
      size={ModalSize.SMALL}
      rightActions={
        <>
          <Button
            variant="bordered"
            color="neutral"
            onClick={() => {
              onDecide(null);
              props.onClose();
            }}
          >
            {t("explorer.convert.file.cancel")}
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              onDecide("yes");
              props.onClose();
            }}
            icon={<Icon name="file_copy" type={IconType.OUTLINED} />}
          >
            {t("explorer.convert.file.confirm")}
          </Button>
        </>
      }
      {...props}
    >
      <div className="c__modal__content__text">
        {t("explorer.convert.file.content")}
      </div>
    </Modal>
  );
};
