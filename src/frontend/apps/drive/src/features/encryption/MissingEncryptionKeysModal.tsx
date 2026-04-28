import { Button, Modal, ModalSize } from '@gouvfr-lasuite/cunningham-react';
import { useTranslation } from 'react-i18next';

/**
 * Heuristic — matches the SDK's "No key pair found" family of errors
 * (encrypt, decrypt, export-public-key, etc.). Used by the global mutation
 * error handler to swap a generic toast for the dedicated modal, and by the
 * file viewer to render a dedicated panel instead of the bare error string.
 */
export const isMissingKeysError = (
  err: Error | string | null | undefined
): boolean => {
  if (!err) return false;
  const msg = typeof err === 'string' ? err : (err.message ?? '');
  return /no key pair/i.test(msg);
};

/** Custom event the global error handler dispatches. */
export const MISSING_KEYS_EVENT = 'vault:missing-keys';

interface MissingEncryptionKeysModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Called when the user accepts — caller opens the onboarding flow. */
  onSetUp: () => void;
}

export const MissingEncryptionKeysModal = ({
  isOpen,
  onClose,
  onSetUp,
}: MissingEncryptionKeysModalProps) => {
  const { t } = useTranslation();
  return (
    <Modal
      isOpen={isOpen}
      closeOnClickOutside
      onClose={onClose}
      size={ModalSize.MEDIUM}
      title={t(
        'encryption.missing_keys.title',
        'Encryption keys required'
      )}
      rightActions={
        <>
          <Button variant="bordered" onClick={onClose}>
            {t('encryption.missing_keys.cancel', 'Not now')}
          </Button>
          <Button onClick={onSetUp}>
            {t('encryption.missing_keys.set_up', 'Set up encryption')}
          </Button>
        </>
      }
    >
      <p style={{ lineHeight: 1.5 }}>
        {t(
          'encryption.missing_keys.body',
          "End-to-end encryption must be enabled on this device before you can continue. Encryption keys are stored locally per-device, so even if you've set them up elsewhere they don't follow you here automatically. To enable encryption on this device, either restore your existing keys from a backup, or generate a brand-new key pair if you've never set them up before."
        )}
      </p>
    </Modal>
  );
};

interface MissingEncryptionKeysPanelProps {
  /** Optional CTA — when provided, a "Set up encryption" button is rendered. */
  onSetUp?: () => void;
}

/**
 * Friendly full-panel placeholder shown when an encrypted file can't be
 * decrypted because the user has no key pair locally.
 */
export const MissingEncryptionKeysPanel = ({
  onSetUp,
}: MissingEncryptionKeysPanelProps = {}) => {
  const { t } = useTranslation();
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        gap: '16px',
        padding: '24px',
        textAlign: 'center',
        maxWidth: '520px',
        margin: '0 auto',
      }}
    >
      <span
        className="material-icons"
        style={{
          fontSize: '48px',
          color: 'var(--c--theme--colors--warning-600, #b15600)',
        }}
      >
        key_off
      </span>
      <span style={{ fontWeight: 600 }}>
        {t(
          'encryption.missing_keys.title',
          'Encryption keys required'
        )}
      </span>
      <span
        style={{
          fontSize: '14px',
          color: 'var(--c--contextuals--content--semantic--neutral--tertiary)',
          lineHeight: 1.5,
        }}
      >
        {t(
          'encryption.missing_keys.viewer_body',
          "This file is encrypted end-to-end. Encryption must be enabled on this device to open it — keys are stored locally per-device and don't follow you across devices automatically. Restore your existing keys from a backup, or generate a brand-new key pair if you've never set them up before."
        )}
      </span>
      {onSetUp && (
        <Button onClick={onSetUp}>
          {t('encryption.missing_keys.set_up', 'Set up encryption')}
        </Button>
      )}
    </div>
  );
};
