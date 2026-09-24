import { Modal, ModalSize } from "@gouvfr-lasuite/cunningham-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { EncryptionHostBody } from "./EncryptionHostBody";
import { useVaultClient } from "./VaultClientProvider";

interface ModalEncryptionSettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * The encryption service's settings draw their own modal over the page; Drive
 * only shows a loader until it is on screen.
 */
export const ModalEncryptionSettings = ({
  isOpen,
  onClose,
}: ModalEncryptionSettingsProps) => {
  const { t } = useTranslation();
  const { client: vaultClient, refreshKeyState } = useVaultClient();
  const openedRef = useRef(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isOpen || !vaultClient || openedRef.current) return;

    openedRef.current = true;
    vaultClient.openSettings();
  }, [isOpen, vaultClient]);

  useEffect(() => {
    if (!vaultClient) return;

    const handleReady = () => setReady(true);

    const handleClosed = () => {
      openedRef.current = false;
      setReady(false);
      refreshKeyState();
      onClose();
    };

    const handleKeysDestroyed = () => {
      refreshKeyState();
    };

    vaultClient.on("interface:ready", handleReady);
    vaultClient.on("interface:closed", handleClosed);
    vaultClient.on("keys-destroyed", handleKeysDestroyed);

    return () => {
      vaultClient.off("interface:ready", handleReady);
      vaultClient.off("interface:closed", handleClosed);
      vaultClient.off("keys-destroyed", handleKeysDestroyed);
    };
  }, [vaultClient, refreshKeyState, onClose]);

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
