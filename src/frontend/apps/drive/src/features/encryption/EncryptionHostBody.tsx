import { Button, Loader } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { EncryptionModalContent } from "./EncryptionLayout";
import { useVaultClient } from "./VaultClientProvider";

interface EncryptionHostBodyProps {
  onClose: () => void;
}

/**
 * What the product shows while the encryption interface comes up. The interface
 * draws its own modal over the page once its SDK has loaded it, so this modal
 * only carries a loader until then, or, if the SDK script itself could not be
 * loaded from the vault domain, an explanation with a retry.
 */
export const EncryptionHostBody = ({ onClose }: EncryptionHostBodyProps) => {
  const { t } = useTranslation();
  const { error } = useVaultClient();

  if (error) {
    return (
      <EncryptionModalContent
        illustration="shield-x"
        title={t(
          "encryption.service_unavailable.title",
          "Encryption service unavailable",
        )}
        description={t(
          "encryption.service_unavailable.body",
          "The encryption service could not be loaded. Check your connection and try again.",
        )}
        actions={
          <>
            <Button onClick={() => window.location.reload()}>
              {t("encryption.service_unavailable.retry", "Retry")}
            </Button>
            <Button variant="bordered" color="neutral" onClick={onClose}>
              {t("encryption.service_unavailable.close", "Close")}
            </Button>
          </>
        }
      />
    );
  }

  return (
    <div className="drive__encryption-host--loading">
      <Loader />
    </div>
  );
};
