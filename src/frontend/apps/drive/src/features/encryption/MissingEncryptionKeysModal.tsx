import { Button, Modal, ModalSize } from "@gouvfr-lasuite/cunningham-react";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { EncryptionModalContent, EncryptionState } from "./EncryptionLayout";

/**
 * True when the SDK threw a `VaultError` carrying the `MISSING_KEYS`
 * code — i.e. the user has no key pair stored locally on this device.
 * Used by the global mutation error handler to swap a generic toast for
 * the dedicated modal, and by the file viewer to render a dedicated
 * panel.
 */
export const isMissingKeysError = (
  err: Error | string | null | undefined,
): boolean => {
  if (!err || typeof err === "string") return false;
  return (err as VaultError).code === "MISSING_KEYS";
};

/** Custom event the global error handler dispatches. */
export const MISSING_KEYS_EVENT = "vault:missing-keys";

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
      size={ModalSize.SMALL}
      aria-label={t(
        "encryption.missing_keys.title",
        "Enable encryption on this device",
      )}
    >
      <EncryptionModalContent
        illustration="shield-check"
        title={t(
          "encryption.missing_keys.title",
          "Enable encryption on this device",
        )}
        description={t(
          "encryption.missing_keys.body",
          "Encryption keys are stored on each device. To continue here, restore your existing keys from another device or your recovery phrase, or enable encryption if you never did.",
        )}
        actions={
          <>
            <Button onClick={onSetUp}>
              {t("encryption.missing_keys.set_up", "Enable encryption")}
            </Button>
            <Button variant="bordered" color="neutral" onClick={onClose}>
              {t("encryption.missing_keys.cancel", "Not now")}
            </Button>
          </>
        }
      />
    </Modal>
  );
};

interface MissingEncryptionKeysPanelProps {
  /** Optional CTA — when provided, an "Enable encryption" link is rendered. */
  onSetUp?: () => void;
}

/**
 * Placeholder shown in the viewer when an encrypted file cannot be decrypted
 * because the user has no key pair on this device.
 */
export const MissingEncryptionKeysPanel = ({
  onSetUp,
}: MissingEncryptionKeysPanelProps = {}) => {
  const { t } = useTranslation();
  return (
    <EncryptionState
      title={t("encryption.missing_keys.viewer_title", "Encrypted file")}
      description={t(
        "encryption.missing_keys.viewer_body",
        "This file is encrypted. You must enable encryption on this device to open it.",
      )}
      actions={
        onSetUp && (
          <Button
            size="small"
            variant="tertiary"
            onClick={onSetUp}
            icon={<Icon aria-hidden name="verified_user" />}
          >
            {t("encryption.missing_keys.set_up", "Enable encryption")}
          </Button>
        )
      }
    />
  );
};
