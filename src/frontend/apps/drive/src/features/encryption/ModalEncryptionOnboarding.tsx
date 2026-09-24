import { Modal, ModalSize } from "@gouvfr-lasuite/cunningham-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { EncryptionHostBody } from "./EncryptionHostBody";
import { useVaultClient } from "./VaultClientProvider";

interface ModalEncryptionOnboardingProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

/**
 * The encryption service's onboarding draws its own modal over the page; Drive
 * only shows a loader until it is on screen.
 */
export const ModalEncryptionOnboarding = ({
  isOpen,
  onClose,
  onSuccess,
}: ModalEncryptionOnboardingProps) => {
  const { t } = useTranslation();
  const { client: vaultClient, refreshKeyState } = useVaultClient();
  const openedRef = useRef(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isOpen || !vaultClient || openedRef.current) return;

    openedRef.current = true;
    vaultClient.openOnboarding();
  }, [isOpen, vaultClient]);

  useEffect(() => {
    if (!vaultClient) return;

    const handleReady = () => setReady(true);

    const handleComplete = async () => {
      await refreshKeyState();
      onSuccess?.();
    };

    const handleClosed = () => {
      openedRef.current = false;
      setReady(false);
      onClose();
    };

    vaultClient.on("interface:ready", handleReady);
    vaultClient.on("onboarding:complete", handleComplete);
    vaultClient.on("interface:closed", handleClosed);

    return () => {
      vaultClient.off("interface:ready", handleReady);
      vaultClient.off("onboarding:complete", handleComplete);
      vaultClient.off("interface:closed", handleClosed);
    };
  }, [vaultClient, refreshKeyState, onSuccess, onClose]);

  // Closing the loader: nothing is at stake before the interface is on screen,
  // so the frame is torn down outright.
  const handleClose = useCallback(() => {
    vaultClient?.closeInterface();
    openedRef.current = false;
    onClose();
  }, [vaultClient, onClose]);

  useEffect(() => {
    if (!isOpen) {
      openedRef.current = false;
      setReady(false);
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen && !ready}
      closeOnClickOutside={false}
      onClose={handleClose}
      size={ModalSize.SMALL}
      aria-label={t("encryption.host_modal.label", "Encryption")}
    >
      <EncryptionHostBody onClose={handleClose} />
    </Modal>
  );
};
