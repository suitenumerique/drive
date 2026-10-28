import { Button } from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";

import { EncryptionState } from "./EncryptionLayout";

/**
 * Why an encrypted file could not be opened:
 * - `key_unavailable`: shared for a key version the user no longer holds
 *   (typically from before they reset their encryption);
 * - `key_mismatch`: the user's key cannot open the copy of the file key
 *   stored for them;
 * - `content_integrity`: the file key opened, the stored content failed its
 *   integrity check (damaged or altered);
 * - `unknown`: anything else.
 */
export type DecryptionFailure =
  | "key_unavailable"
  | "key_mismatch"
  | "content_integrity"
  | "unknown";

export const decryptionFailureOf = (
  code: string | null | undefined,
): DecryptionFailure => {
  switch (code) {
    case "KEY_VERSION_UNAVAILABLE":
      return "key_unavailable";
    case "WRONG_SECRET_KEY":
      return "key_mismatch";
    case "CONTENT_INTEGRITY_FAILED":
    case "MALFORMED_CIPHERTEXT":
    case "CIPHERTEXT_TOO_SHORT":
    case "UNSUPPORTED_CRYPTO_VERSION":
      return "content_integrity";
    default:
      return "unknown";
  }
};

/** Shown instead of the file when an encrypted file cannot be opened. */
export const DecryptionFailurePanel = ({
  failure,
}: {
  failure: DecryptionFailure;
}) => {
  const { t } = useTranslation();

  const copy = {
    key_unavailable: {
      title: t(
        "explorer.encrypted.decryption_failure.key_unavailable.title",
        "This file was shared with a previous key",
      ),
      description: t(
        "explorer.encrypted.decryption_failure.key_unavailable.body",
        "That key is no longer on your account, most likely because you reset your encryption. Ask the file owner to remove you from its members and add you again.",
      ),
    },
    key_mismatch: {
      title: t(
        "explorer.encrypted.decryption_failure.key_mismatch.title",
        "This file was encrypted with a different key",
      ),
      description: t(
        "explorer.encrypted.decryption_failure.key_mismatch.body",
        "Your current encryption key cannot open it. Ask the file owner to remove you from its members and add you again.",
      ),
    },
    content_integrity: {
      title: t(
        "explorer.encrypted.decryption_failure.content_integrity.title",
        "This file cannot be decrypted",
      ),
      description: t(
        "explorer.encrypted.decryption_failure.content_integrity.body",
        "Your key is correct, but the stored content is damaged or was altered, so it cannot be trusted. Contact the owner of this file or your support.",
      ),
    },
    unknown: {
      title: t(
        "explorer.encrypted.decryption_failure.unknown.title",
        "This file could not be decrypted",
      ),
      description: t(
        "explorer.encrypted.decryption_failure.unknown.body",
        "Something went wrong while decrypting this file. Try again.",
      ),
    },
  }[failure];

  return (
    <EncryptionState
      title={copy.title}
      description={copy.description}
      actions={
        failure === "unknown" ? (
          <Button
            size="small"
            variant="tertiary"
            onClick={() => window.location.reload()}
          >
            {t("encryption.service_unavailable.retry", "Retry")}
          </Button>
        ) : undefined
      }
    />
  );
};
