import { Button, Modal, ModalSize } from '@gouvfr-lasuite/cunningham-react';
import { useTranslation } from 'react-i18next';
import { Item } from '@/features/drivers/types';

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
 */
export const ModalEncryptionNotRoot = ({ isOpen, onClose, item }: Props) => {
  const { t } = useTranslation();

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
    </Modal>
  );
};
