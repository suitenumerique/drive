import { Modal, ModalSize } from '@gouvfr-lasuite/cunningham-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useVaultClient } from './VaultClientProvider';

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

    vaultClient.on('onboarding:complete', handleComplete);
    vaultClient.on('interface:closed', handleClosed);

    return () => {
      vaultClient.off('onboarding:complete', handleComplete);
      vaultClient.off('interface:closed', handleClosed);
    };
  }, [vaultClient, refreshKeyState, onSuccess, onClose]);

  const handleClose = useCallback(() => {
    vaultClient?.closeInterface();
    onboardingOpenedRef.current = false;
    onClose();
  }, [vaultClient, onClose]);

  useEffect(() => {
    if (!isOpen) {
      onboardingOpenedRef.current = false;
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      closeOnClickOutside
      onClose={handleClose}
      size={ModalSize.LARGE}
    >
      <div style={{ minHeight: '400px' }}>
        <div
          ref={setContainerEl}
          style={{ width: '100%', minHeight: '400px' }}
        />
      </div>
    </Modal>
  );
};
