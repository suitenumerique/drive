import { useCallback, useEffect, useRef, useState } from "react";
import { Item } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";

/**
 * Hook that fetches an encrypted file, decrypts it via the vault,
 * and returns a blob URL for preview or download.
 *
 * The blob URL is automatically revoked on unmount or when the item changes.
 *
 * Requires the vault client to be initialized and the user to have
 * encryption keys. The key chain is resolved automatically.
 */
export const useDecryptedContent = (item?: Item) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isDecrypting, setIsDecrypting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  // Clean up blob URL on unmount or item change
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [item?.id]);

  const decrypt = useCallback(async () => {
    if (!item?.url || !item?.is_encrypted) {
      return null;
    }

    setIsDecrypting(true);
    setError(null);

    try {
      const driver = getDriver();

      // 1. Get the key chain for this item
      const keyChain = await driver.getKeyChain(item.id);

      // 2. Fetch the encrypted file content
      const response = await fetch(item.url, { credentials: "include" });
      if (!response.ok) {
        throw new Error(`Failed to fetch encrypted file: ${response.status}`);
      }
      const encryptedBuffer = await response.arrayBuffer();

      // 3. Decrypt via vault with key chain
      // The vault client must be available on window (loaded by VaultClientProvider)
      const vaultClient = (window as any).__driveVaultClient;
      if (!vaultClient) {
        throw new Error(
          "Vault client not initialized. Encryption keys are required.",
        );
      }

      const encryptedKeyChain = keyChain.chain.map((entry) => {
        // Convert base64 to ArrayBuffer
        const binary = atob(entry.encrypted_symmetric_key);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
      });

      // Convert entry-point key from base64 to ArrayBuffer
      const entryKeyBinary = atob(keyChain.encrypted_key_for_user);
      const entryKeyBytes = new Uint8Array(entryKeyBinary.length);
      for (let i = 0; i < entryKeyBinary.length; i++) {
        entryKeyBytes[i] = entryKeyBinary.charCodeAt(i);
      }
      const encryptedSymmetricKey = entryKeyBytes.buffer;

      const { data: decryptedBuffer } = await vaultClient.decryptWithKey(
        encryptedBuffer,
        encryptedSymmetricKey,
        encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined,
      );

      // 4. Create blob URL
      const blob = new Blob([decryptedBuffer], {
        type: item.mimetype || "application/octet-stream",
      });
      const url = URL.createObjectURL(blob);

      // Clean up previous blob URL
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
      blobUrlRef.current = url;
      setBlobUrl(url);

      return url;
    } catch (err) {
      const error =
        err instanceof Error ? err : new Error("Decryption failed");
      setError(error);
      return null;
    } finally {
      setIsDecrypting(false);
    }
  }, [item?.id, item?.url, item?.is_encrypted, item?.mimetype]);

  // Auto-decrypt when the item changes
  useEffect(() => {
    if (item?.is_encrypted && item?.url) {
      decrypt();
    }
  }, [item?.id]);

  return { blobUrl, isDecrypting, error, decrypt };
};

/**
 * Download an encrypted file by decrypting it client-side and triggering
 * a browser download with the decrypted content.
 */
export const downloadDecryptedFile = async (
  item: Item,
): Promise<void> => {
  const driver = getDriver();

  // 1. Get the key chain
  const keyChain = await driver.getKeyChain(item.id);

  // 2. Fetch encrypted content
  const response = await fetch(item.url!, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Failed to fetch encrypted file: ${response.status}`);
  }
  const encryptedBuffer = await response.arrayBuffer();

  // 3. Decrypt via vault
  const vaultClient = (window as any).__driveVaultClient;
  if (!vaultClient) {
    throw new Error("Vault client not initialized.");
  }

  const encryptedKeyChain = keyChain.chain.map((entry) => {
    const binary = atob(entry.encrypted_symmetric_key);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  });

  const entryKeyBinary = atob(keyChain.encrypted_key_for_user);
  const entryKeyBytes = new Uint8Array(entryKeyBinary.length);
  for (let i = 0; i < entryKeyBinary.length; i++) {
    entryKeyBytes[i] = entryKeyBinary.charCodeAt(i);
  }

  const { data: decryptedBuffer } = await vaultClient.decryptWithKey(
    encryptedBuffer,
    entryKeyBytes.buffer,
    encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined,
  );

  // 4. Create blob and trigger download
  const blob = new Blob([decryptedBuffer], {
    type: item.mimetype || "application/octet-stream",
  });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.style.display = "none";
  a.href = url;
  a.download = item.title;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  URL.revokeObjectURL(url);
};
