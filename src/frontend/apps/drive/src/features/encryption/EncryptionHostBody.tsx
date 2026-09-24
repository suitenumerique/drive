import { Button, Loader, ModalSize } from "@gouvfr-lasuite/cunningham-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { EncryptionModalContent } from "./EncryptionLayout";
import { useVaultClient } from "./VaultClientProvider";

/**
 * The size the interface asks for its host modal: small (350px) by default, the
 * design system's medium one when the shown screen needs the room. Resets to
 * small whenever the modal closes, so the next opening starts at the default.
 */
export const useInterfaceModalSize = (isOpen: boolean): ModalSize => {
  const { client } = useVaultClient();
  const [size, setSize] = useState<ModalSize>(ModalSize.SMALL);

  useEffect(() => {
    if (!client) return;

    const handleSize = ({ size: wanted }: { size: "small" | "medium" }) => {
      setSize(wanted === "medium" ? ModalSize.MEDIUM : ModalSize.SMALL);
    };

    client.on("interface:size", handleSize);

    return () => {
      client.off("interface:size", handleSize);
    };
  }, [client]);

  useEffect(() => {
    if (!isOpen) setSize(ModalSize.SMALL);
  }, [isOpen]);

  return size;
};

interface EncryptionHostBodyProps {
  /** Receives the element the interface iframe is mounted into. */
  hostRef: (element: HTMLDivElement | null) => void;
  onClose: () => void;
}

/**
 * The body of a modal hosting the encryption interface. The interface can only
 * be opened once the SDK script has loaded from the vault domain: until then a
 * loader, and if that load failed an explanation with a retry, instead of the
 * empty host the interface would otherwise never fill.
 */
export const EncryptionHostBody = ({
  hostRef,
  onClose,
}: EncryptionHostBodyProps) => {
  const { t } = useTranslation();
  const { client, isLoading, error } = useVaultClient();

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

  if (!client || isLoading) {
    return (
      <div className="drive__encryption-host drive__encryption-host--loading">
        <Loader />
      </div>
    );
  }

  return <div ref={hostRef} className="drive__encryption-host" />;
};
