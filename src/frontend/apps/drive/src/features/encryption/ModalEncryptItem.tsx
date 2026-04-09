import { Button, Modal, ModalSize } from '@gouvfr-lasuite/cunningham-react';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { Item, LinkReach } from '@/features/drivers/types';
import { useVaultClient } from './VaultClientProvider';
import { getDriver } from '@/features/config/Config';
import {
  addToast,
  ToasterItem,
} from '@/features/ui/components/toaster/Toaster';

interface ModalEncryptItemProps {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
}

function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export const ModalEncryptItem = ({
  isOpen,
  onClose,
  item,
}: ModalEncryptItemProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { client: vaultClient, hasKeys } = useVaultClient();
  const [isEncrypting, setIsEncrypting] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [publicKeysReady, setPublicKeysReady] = useState(false);

  // Validate preconditions
  useEffect(() => {
    if (!isOpen) return;

    const errors: string[] = [];

    if (!hasKeys) {
      errors.push(
        t(
          'encryption.errors.no_keys',
          'You need to enable encryption first (from the user menu).'
        )
      );
    }

    const effectiveReach = item.computed_link_reach ?? item.link_reach;
    if (effectiveReach && effectiveReach !== LinkReach.RESTRICTED) {
      errors.push(
        t(
          'encryption.errors.not_restricted',
          'Item must have restricted access (no public or authenticated links).'
        )
      );
    }

    if (!item.accesses_user_ids || item.accesses_user_ids.length === 0) {
      errors.push(
        t(
          'encryption.errors.no_accesses',
          'No users with access found for this item.'
        )
      );
    }

    setValidationErrors(errors);
    setPublicKeysReady(false);
  }, [isOpen, hasKeys, item, t]);

  // Fetch public keys for all users with access
  useEffect(() => {
    if (
      !isOpen ||
      !vaultClient ||
      !item.accesses_user_ids?.length ||
      validationErrors.length > 0
    ) {
      return;
    }

    let cancelled = false;

    async function checkPublicKeys() {
      try {
        const { publicKeys } = await vaultClient!.fetchPublicKeys(
          item.accesses_user_ids!
        );

        if (cancelled) return;

        const missingUsers = item.accesses_user_ids!.filter(
          uid => !publicKeys[uid]
        );

        if (missingUsers.length > 0) {
          setValidationErrors(prev => [
            ...prev,
            t(
              'encryption.errors.missing_keys',
              "Some users don't have encryption enabled yet ({{count}} user(s)).",
              { count: missingUsers.length }
            ),
          ]);
          setPublicKeysReady(false);
        } else {
          setPublicKeysReady(true);
        }
      } catch {
        if (!cancelled) {
          setValidationErrors(prev => [
            ...prev,
            t(
              'encryption.errors.fetch_keys_failed',
              'Failed to fetch public keys.'
            ),
          ]);
        }
      }
    }

    void checkPublicKeys();

    return () => {
      cancelled = true;
    };
  }, [isOpen, vaultClient, item.accesses_user_ids, validationErrors.length, t]);

  const handleEncrypt = useCallback(async () => {
    if (!vaultClient || !item.accesses_user_ids?.length || !item.url) return;

    setIsEncrypting(true);

    try {
      // 1. Fetch public keys for all users with access
      const { publicKeys } = await vaultClient.fetchPublicKeys(
        item.accesses_user_ids
      );

      // 2. Download the plaintext file from S3
      const fileResponse = await fetch(item.url, { credentials: 'include' });
      if (!fileResponse.ok) {
        throw new Error(`Failed to download file: ${fileResponse.status}`);
      }
      const plaintextContent = await fileResponse.arrayBuffer();

      // 3. Encrypt the content + generate per-user wrapped keys
      const { encryptedContent, encryptedKeys } =
        await vaultClient.encryptWithoutKey(plaintextContent, publicKeys);

      // 4. Get a presigned upload URL for the new filename
      const newFilename = `${crypto.randomUUID()}.enc`;
      const { fetchAPI } = await import('@/features/api/fetchApi');
      const uploadUrlResp = await fetchAPI(
        `items/${item.id}/encryption-upload-url/`,
        {
          method: 'POST',
          body: JSON.stringify({ filename: newFilename }),
        }
      );
      if (!uploadUrlResp.ok) {
        throw new Error('Failed to get upload URL for encrypted file');
      }
      const { upload_url: uploadUrl } = await uploadUrlResp.json();

      // 5. Upload encrypted content to the new S3 key
      const uploadResponse = await fetch(uploadUrl, {
        method: 'PUT',
        body: new Uint8Array(encryptedContent),
        headers: { 'X-amz-acl': 'private' },
      });
      if (!uploadResponse.ok) {
        throw new Error(
          `Failed to upload encrypted file: ${uploadResponse.status}`
        );
      }

      // 6. Convert wrapped keys to base64
      const encryptedSymmetricKeyPerUser: Record<string, string> = {};
      for (const [uid, keyBuffer] of Object.entries(encryptedKeys)) {
        encryptedSymmetricKeyPerUser[uid] = toBase64(keyBuffer);
      }

      // 7. Call backend to atomically update DB (mark encrypted + swap filename)
      const driver = getDriver();
      await driver.encryptItem(item.id, {
        encryptedSymmetricKeyPerUser,
        encryptedKeysForDescendants: {},
        fileKeyMapping: { [item.id]: newFilename },
      });

      // Invalidate all item queries to refresh the list
      await queryClient.invalidateQueries({ queryKey: ['items'] });
      await queryClient.invalidateQueries({
        queryKey: ['items', item.id],
      });

      addToast(
        <ToasterItem type="success">
          <span>{t('encryption.success', 'Item encrypted successfully.')}</span>
        </ToasterItem>
      );

      onClose();
    } catch (err) {
      addToast(
        <ToasterItem type="error">
          <span>
            {t('encryption.error', 'Encryption failed: {{message}}', {
              message: (err as Error).message,
            })}
          </span>
        </ToasterItem>
      );
    } finally {
      setIsEncrypting(false);
    }
  }, [vaultClient, item, onClose, t]);

  const canEncrypt =
    validationErrors.length === 0 && publicKeysReady && hasKeys;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      closeOnClickOutside
      size={ModalSize.MEDIUM}
      title={t('encryption.modal.title', 'Encrypt item')}
      actions={
        <>
          <Button color="secondary" onClick={onClose} disabled={isEncrypting}>
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button
            onClick={handleEncrypt}
            disabled={!canEncrypt || isEncrypting}
            aria-busy={isEncrypting}
          >
            {isEncrypting
              ? t('encryption.modal.encrypting', 'Encrypting...')
              : t('encryption.modal.confirm', 'Encrypt')}
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <p>
          {t(
            'encryption.modal.description',
            'You are about to encrypt "{{title}}". Once encrypted, the item can only be accessed by users with encryption keys.',
            { title: item.title }
          )}
        </p>

        {validationErrors.length > 0 && (
          <div
            style={{
              padding: '0.75rem',
              backgroundColor: 'var(--c--theme--colors--danger-100, #fde8e8)',
              borderRadius: '4px',
            }}
          >
            <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
              {validationErrors.map((err, i) => (
                <li
                  key={i}
                  style={{
                    color: 'var(--c--theme--colors--danger-text, #c00)',
                  }}
                >
                  {err}
                </li>
              ))}
            </ul>
          </div>
        )}

        {validationErrors.length === 0 && !publicKeysReady && (
          <p
            style={{
              color: 'var(--c--theme--colors--greyscale-600, #666)',
            }}
          >
            {t(
              'encryption.modal.checking_keys',
              'Checking encryption keys for all users...'
            )}
          </p>
        )}
      </div>
    </Modal>
  );
};
