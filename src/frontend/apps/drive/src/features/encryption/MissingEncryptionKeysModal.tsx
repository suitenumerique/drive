import { Button, Modal, ModalSize } from "@gouvfr-lasuite/ui-components";
import { House, ShieldCheck } from "@gouvfr-lasuite/ui-components/icons";
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
  /** Opens the onboarding; without it the panel only explains. */
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
        <>
          <EncryptionHomeButton />
          {onSetUp && <EnableEncryptionButton size="small" onClick={onSetUp} />}
        </>
      }
    />
  );
};

/**
 * The primary action wherever Drive needs the user to enable encryption first:
 * it opens the encryption service's onboarding over the page, never a detour
 * through another menu.
 */
export const EnableEncryptionButton = ({
  onClick,
  size,
}: {
  onClick: () => void;
  /** Small in a viewer's state, beside the Home button. */
  size?: "small";
}) => {
  const { t } = useTranslation();
  return (
    <Button size={size} onClick={onClick} icon={<ShieldCheck aria-hidden />}>
      {t("encryption.missing_keys.set_up", "Enable encryption")}
    </Button>
  );
};

/**
 * The way out of a viewer that cannot show an encrypted file: back to the
 * user's files, as on Docs' encrypted document states.
 */
export const EncryptionHomeButton = () => {
  const { t } = useTranslation();
  return (
    <Button
      href="/"
      size="small"
      color="neutral"
      variant="tertiary"
      icon={<House aria-hidden />}
    >
      {t("encryption.missing_keys.home", "Home")}
    </Button>
  );
};
