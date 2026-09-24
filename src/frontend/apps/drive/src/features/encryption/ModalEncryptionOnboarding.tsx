import { Modal } from "@gouvfr-lasuite/cunningham-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  EncryptionHostBody,
  useInterfaceModalSize,
} from "./EncryptionHostBody";
import { useVaultClient } from "./VaultClientProvider";

interface ModalEncryptionOnboardingProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const ModalEncryptionOnboarding = ({
  isOpen,
  onClose,
  onSuccess,
}: ModalEncryptionOnboardingProps) => {
  const { t } = useTranslation();
  const { client: vaultClient, refreshKeyState } = useVaultClient();
  const onboardingOpenedRef = useRef(false);
  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (
      !isOpen ||
      !vaultClient ||
      !containerEl ||
      onboardingOpenedRef.current
    ) {
      return;
    }

    onboardingOpenedRef.current = true;
    vaultClient.openOnboarding(containerEl);
  }, [isOpen, vaultClient, containerEl]);

  useEffect(() => {
    if (!vaultClient) return;

    const handleComplete = async () => {
      await refreshKeyState();
      onSuccess?.();
    };

    const handleClosed = () => {
      onboardingOpenedRef.current = false;
      onClose();
    };

    vaultClient.on("onboarding:complete", handleComplete);
    vaultClient.on("interface:closed", handleClosed);

    return () => {
      vaultClient.off("onboarding:complete", handleComplete);
      vaultClient.off("interface:closed", handleClosed);
    };
  }, [vaultClient, refreshKeyState, onSuccess, onClose]);

  // The modal's close control only ASKS the interface to close: it may hold an
  // unsaved recovery phrase and answer with its own confirmation. The modal goes
  // away on 'interface:closed', which the interface emits once really done.
  const handleClose = useCallback(() => {
    if (vaultClient) vaultClient.requestClose();
    else onClose();
  }, [vaultClient, onClose]);

  useEffect(() => {
    if (!isOpen) {
      onboardingOpenedRef.current = false;
    }
  }, [isOpen]);

  const size = useInterfaceModalSize(isOpen);

  return (
    <Modal
      isOpen={isOpen}
      closeOnClickOutside={false}
      onClose={handleClose}
      size={size}
      aria-label={t("encryption.host_modal.label", "Encryption")}
    >
      <EncryptionHostBody hostRef={setContainerEl} onClose={onClose} />
    </Modal>
  );
};
