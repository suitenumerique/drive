import { Modal, ModalSize } from "@gouvfr-lasuite/cunningham-react";
import { useCallback, useEffect, useState } from "react";
import { useVaultClient } from "./VaultClientProvider";

interface ModalEncryptionSettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ModalEncryptionSettings = ({
  isOpen,
  onClose,
}: ModalEncryptionSettingsProps) => {
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

  const handleClose = useCallback(() => {
    vaultClient?.closeInterface();
    setSettingsOpened(false);
    onClose();
  }, [vaultClient, onClose]);

  useEffect(() => {
    if (!isOpen) {
      setSettingsOpened(false);
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      closeOnClickOutside
      onClose={handleClose}
      size={ModalSize.LARGE}
    >
      <div style={{ minHeight: "400px" }}>
        <div
          ref={setContainerEl}
          style={{ width: "100%", minHeight: "400px" }}
        />
      </div>
    </Modal>
  );
};
