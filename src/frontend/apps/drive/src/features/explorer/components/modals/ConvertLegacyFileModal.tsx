import { useState } from "react";
import { Button, Modal, ModalSize } from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { Item, ItemUploadState } from "@/features/drivers/types";
import { useMutationConvertItem } from "@/features/explorer/hooks/useMutations";

type Props = {
  item: Item;
  isOpen: boolean;
  onClose: () => void;
};

export const ConvertLegacyFileModal = ({ item, isOpen, onClose }: Props) => {
  const { t } = useTranslation();
  const convertMutation = useMutationConvertItem();
  const [error, setError] = useState<string | null>(null);
  const isSubmitting = convertMutation.isPending;

  const handleClose = () => {
    if (isSubmitting) return;
    setError(null);
    onClose();
  };

  const handleConvert = async () => {
    setError(null);
    try {
      await convertMutation.mutateAsync(item.id);
      onClose();
    } catch {
      setError(t("explorer.actions.convert.modal.error"));
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={t("explorer.actions.convert.modal.title")}
      size={ModalSize.MEDIUM}
      preventClose={isSubmitting}
      rightActions={
        <>
          <Button
            variant="bordered"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            {t("explorer.actions.convert.modal.cancel")}
          </Button>
          <Button onClick={handleConvert} disabled={isSubmitting}>
            {t("explorer.actions.convert.modal.confirm")}
          </Button>
        </>
      }
    >
      <div className="c__modal__content__text">
        {error ? (
          <p className="clr-error-500">{error}</p>
        ) : (
          <>
            {t("explorer.actions.convert.modal.content")}
            {item.upload_state === ItemUploadState.ANALYZING && (
              <p>{t("explorer.actions.convert.modal.analyzing_notice")}</p>
            )}
          </>
        )}
      </div>
    </Modal>
  );
};
