import { Button, Modal, ModalSize } from "@gouvfr-lasuite/cunningham-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { Item } from "@/features/drivers/types";
import { useVaultClient } from "./VaultClientProvider";
import { getDriver } from "@/features/config/Config";
import { fetchAPI } from "@/features/api/fetchApi";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";

interface ModalRemoveEncryptionProps {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
}

export const ModalRemoveEncryption = ({
  isOpen,
  onClose,
  item,
}: ModalRemoveEncryptionProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { client: vaultClient } = useVaultClient();
  const [isDecrypting, setIsDecrypting] = useState(false);

  const handleRemoveEncryption = useCallback(async () => {
    if (!vaultClient || !item.url) return;

    setIsDecrypting(true);

    try {
      const driver = getDriver();

      // 1. Get the key chain for decryption
      const keyChain = await driver.getKeyChain(item.id);

      // Convert base64 keys to ArrayBuffer
      const entryKeyBinary = atob(keyChain.encrypted_key_for_user);
      const entryKeyBytes = new Uint8Array(entryKeyBinary.length);
      for (let i = 0; i < entryKeyBinary.length; i++) {
        entryKeyBytes[i] = entryKeyBinary.charCodeAt(i);
      }

      const encryptedKeyChain = keyChain.chain.map((entry) => {
        const binary = atob(entry.encrypted_symmetric_key);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
      });

      // 2. Download the encrypted file
      const fileResponse = await fetch(item.url, { credentials: "include" });
      if (!fileResponse.ok) {
        throw new Error(`Failed to download file: ${fileResponse.status}`);
      }
      const encryptedContent = await fileResponse.arrayBuffer();

      // 3. Decrypt via vault
      const { data: plaintextContent } = await vaultClient.decryptWithKey(
        encryptedContent,
        entryKeyBytes.buffer,
        encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined,
      );

      // 4. Get presigned URL for the new plaintext filename
      const newFilename = `${crypto.randomUUID()}.dec`;
      const uploadUrlResp = await fetchAPI(
        `items/${item.id}/encryption-upload-url/`,
        {
          method: "POST",
          body: JSON.stringify({ filename: newFilename }),
        },
      );
      if (!uploadUrlResp.ok) {
        throw new Error("Failed to get upload URL");
      }
      const { upload_url: uploadUrl } = await uploadUrlResp.json();

      // 5. Upload plaintext content to the new S3 key
      const uploadResponse = await fetch(uploadUrl, {
        method: "PUT",
        body: new Uint8Array(plaintextContent),
        headers: { "X-amz-acl": "private" },
      });
      if (!uploadResponse.ok) {
        throw new Error(`Failed to upload decrypted file: ${uploadResponse.status}`);
      }

      // 6. Call backend to atomically remove encryption + swap filename
      await driver.removeEncryption(item.id, {
        fileKeyMapping: { [item.id]: newFilename },
      });

      // Refresh the list
      await queryClient.invalidateQueries({ queryKey: ["items"] });

      addToast(
        <ToasterItem type="success">
          <span>
            {t(
              "encryption.remove_success",
              "Encryption removed successfully.",
            )}
          </span>
        </ToasterItem>,
      );

      onClose();
    } catch (err) {
      addToast(
        <ToasterItem type="error">
          <span>
            {t(
              "encryption.remove_error",
              "Failed to remove encryption: {{message}}",
              { message: (err as Error).message },
            )}
          </span>
        </ToasterItem>,
      );
    } finally {
      setIsDecrypting(false);
    }
  }, [vaultClient, item, onClose, queryClient, t]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      closeOnClickOutside
      size={ModalSize.MEDIUM}
      title={t(
        "encryption.remove_modal.title",
        "Remove encryption",
      )}
      actions={
        <>
          <Button color="secondary" onClick={onClose} disabled={isDecrypting}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            color="danger"
            onClick={handleRemoveEncryption}
            disabled={isDecrypting}
            aria-busy={isDecrypting}
          >
            {isDecrypting
              ? t("encryption.remove_modal.decrypting", "Removing encryption...")
              : t("encryption.remove_modal.confirm", "Remove encryption")}
          </Button>
        </>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <p>
          {t(
            "encryption.remove_modal.description",
            'You are about to remove encryption from "{{title}}". The file content will be decrypted and stored in plain.',
            { title: item.title },
          )}
        </p>
      </div>
    </Modal>
  );
};
