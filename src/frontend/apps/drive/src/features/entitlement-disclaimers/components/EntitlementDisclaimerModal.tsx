import {
  Button,
  Modal,
  ModalSize,
  useModal,
} from "@gouvfr-lasuite/cunningham-react";
import { ReactNode } from "react";
import { useTranslation } from "react-i18next";

type EntitlementDisclaimerModalProps = {
  title: ReactNode;
  description: ReactNode;
};

export const EntitlementDisclaimerModal = ({
  title,
  description,
}: EntitlementDisclaimerModalProps) => {
  const modal = useModal({ isOpenDefault: true });
  const { t } = useTranslation();

  return (
    <Modal
      {...modal}
      size={ModalSize.MEDIUM}
      title={title}
      rightActions={
        <Button variant="primary" onClick={modal.close}>
          {t("entitlements.disclaimers.close")}
        </Button>
      }
    >
      {description}
    </Modal>
  );
};
