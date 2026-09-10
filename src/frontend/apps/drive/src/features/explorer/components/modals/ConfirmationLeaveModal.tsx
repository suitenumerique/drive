import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { Item } from "@/features/drivers/types";
import { useMutationLeaveItem } from "../../hooks/useMutations";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useRouter } from "next/router";
import { getParentIdFromPath, setManualNavigationItemId } from "../../utils/utils";

export const ConfirmationLeaveModal = ({
  item,
  ...props
}: Pick<ModalProps, "isOpen" | "onClose"> & { item: Item }) => {
  const { t } = useTranslation();
  const router = useRouter();
  const { mutateAsync: leaveItem, isPending } = useMutationLeaveItem();

  const handleLeave = async () => {
    try {
      await leaveItem(item.id);
      props.onClose();
      addToast(
        <ToasterItem>
          <span className="material-icons">logout</span>
          <span>{t("explorer.item.actions.leave_toast")}</span>
        </ToasterItem>,
      );
      const parentId = getParentIdFromPath(item.path);
      if (parentId) {
        setManualNavigationItemId(parentId);
        router.push(`/explorer/items/${parentId}`);
      } else {
        router.push(`/explorer/items/shared-with-me`);
      }
    } catch {
      addToast(
        <ToasterItem type="error">
          <span className="material-icons">logout</span>
          <span>{t("explorer.item.actions.leave_toast_error")}</span>
        </ToasterItem>,
      );
    }
  };

  return (
    <Modal
      {...props}
      title={t("explorer.item.actions.leave_modal.title")}
      size={ModalSize.MEDIUM}
      rightActions={
        <>
          <Button variant="bordered" onClick={props.onClose}>
            {t("explorer.item.actions.leave_modal.cancel")}
          </Button>
          <Button color="error" onClick={handleLeave} disabled={isPending}>
            {t("explorer.item.actions.leave_modal.confirm")}
          </Button>
        </>
      }
    >
      <div className="c__modal__content__text">
        {t("explorer.item.actions.leave_modal.content")}
      </div>
    </Modal>
  );
};
