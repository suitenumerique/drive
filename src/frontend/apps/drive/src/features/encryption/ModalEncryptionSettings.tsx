import { Modal } from "@gouvfr-lasuite/cunningham-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  EncryptionHostBody,
  useInterfaceModalSize,
} from "./EncryptionHostBody";
import { useVaultClient } from "./VaultClientProvider";

interface ModalEncryptionSettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ModalEncryptionSettings = ({
  isOpen,
  onClose,
}: ModalEncryptionSettingsProps) => {
  const { t } = useTranslation();
  const { client: vaultClient, refreshKeyState } = useVaultClient();
  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);
  const [settingsOpened, setSettingsOpened] = useState(false);

  useEffect(() => {
    if (!isOpen || !vaultClient || !containerEl || settingsOpened) {
      return;
    }

    setSettingsOpened(true);
    vaultClient.openSettings(containerEl);
  }, [isOpen, vaultClient, containerEl, settingsOpened]);

  useEffect(() => {
    if (!vaultClient) return;

    const handleClosed = () => {
      setSettingsOpened(false);
      refreshKeyState();
      onClose();
    };

    const handleKeysDestroyed = () => {
      refreshKeyState();
    };

    vaultClient.on("interface:closed", handleClosed);
    vaultClient.on("keys-destroyed", handleKeysDestroyed);

    return () => {
      vaultClient.off("interface:closed", handleClosed);
      vaultClient.off("keys-destroyed", handleKeysDestroyed);
    };
  }, [vaultClient, refreshKeyState, onClose]);

  // The modal's close control only ASKS the interface to close: it may hold an
  // unsaved recovery phrase and answer with its own confirmation. The modal goes
  // away on 'interface:closed', which the interface emits once really done.
  const handleClose = useCallback(() => {
    if (vaultClient) vaultClient.requestClose();
    else onClose();
  }, [vaultClient, onClose]);

  useEffect(() => {
    if (!isOpen) {
      setSettingsOpened(false);
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
