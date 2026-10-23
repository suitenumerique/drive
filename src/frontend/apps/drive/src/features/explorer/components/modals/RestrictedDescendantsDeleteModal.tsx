import { Button, Modal, ModalSize } from "@gouvfr-lasuite/ui-components";
import { Trans, useTranslation } from "react-i18next";

export const RestrictedDescendantsDeleteModal = ({
  count,
  onDecide,
}: {
  count: number;
  onDecide: (confirmed: boolean) => void;
}) => {
  const { t } = useTranslation();
  return (
    <Modal
      isOpen
      onClose={() => onDecide(false)}
      title={t("explorer.actions.delete.confirmation.title", { count })}
      size={ModalSize.SMALL}
      rightActions={
        <>
          <Button
            color="neutral"
            variant="bordered"
            onClick={() => onDecide(false)}
          >
            {t("explorer.actions.delete.confirmation.cancel")}
          </Button>
          <Button color="error" onClick={() => onDecide(true)}>
            {t("explorer.actions.delete.confirmation.confirm")}
          </Button>
        </>
      }
    >
      <div className="c__modal__content__text">
        <Trans
          i18nKey="explorer.actions.delete.confirmation.content"
          count={count}
          components={{ strong: <strong /> }}
        />
      </div>
    </Modal>
  );
};
