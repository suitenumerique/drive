import { Button, Modal, ModalSize } from '@gouvfr-lasuite/cunningham-react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Item } from '@/features/drivers/types';
import { getDriver } from '@/features/config/Config';
import { useBreadcrumbQuery } from '@/features/explorer/hooks/useBreadcrumb';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
}

/**
 * Shown when the user picks "Remove encryption" on an item that isn't the
 * encryption root (a file or nested folder inside an already-encrypted
 * subtree). Encryption lives at the subtree root, so removal has to happen
 * there — doing it would decrypt every descendant atomically.
 *
 * We display the breadcrumb to the outer encryption root so the user
 * knows exactly where to navigate to retry the action.
 */
export const ModalEncryptionNotRoot = ({ isOpen, onClose, item }: Props) => {
  const { t } = useTranslation();

  // Resolve the encryption root via /key-chain/: it returns
  // `user_access_item_id` which is the ancestor where the user's
  // wrapped key lives — the outer encryption root for this item.
  const { data: keyChain } = useQuery({
    queryKey: ['key-chain', item.id],
    queryFn: () => getDriver().getKeyChain(item.id),
    enabled: isOpen,
  });
  const rootId = keyChain?.user_access_item_id;

  // Fetch the breadcrumb (root-first) for that encryption root so we
  // can render the full path the user should navigate to.
  const { data: rootBreadcrumb } = useBreadcrumbQuery(rootId);

  const rootPath = rootBreadcrumb?.map((b) => b.title).join(' › ');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size={ModalSize.MEDIUM}
      title={t(
        'encryption.not_root_modal.title',
        'Encryption cannot be removed here',
      )}
      actions={
        <Button onClick={onClose}>
          {t('common.got_it', 'Got it')}
        </Button>
      }
    >
      <p style={{ margin: 0 }}>
        {t(
          'encryption.not_root_modal.body',
          '"{{title}}" is inside an encrypted folder. Encryption can only be removed from the top folder where it was applied — which will also decrypt every file inside.',
          { title: item.title },
        )}
      </p>
      {rootPath && (
        <p
          style={{
            margin: '0.75rem 0 0 0',
            padding: '0.5rem 0.75rem',
            borderRadius: '4px',
            background:
              'var(--c--theme--colors--greyscale-100, #f4f4f5)',
            fontSize: '0.9rem',
          }}
          title={rootPath}
        >
          {t('encryption.not_root_modal.root_path', 'Top folder:')}{' '}
          <strong>{rootPath}</strong>
        </p>
      )}
    </Modal>
  );
};
