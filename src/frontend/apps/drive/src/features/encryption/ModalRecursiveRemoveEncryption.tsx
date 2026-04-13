import { Button, Modal, ModalSize } from '@gouvfr-lasuite/cunningham-react';
import { useTranslation } from 'react-i18next';
import { Item, ItemType } from '@/features/drivers/types';
import { useRecursiveEncryptionJob } from './recursive/useRecursiveEncryptionJob';
import { JobFileRow } from './recursive/JobFileRow';
import { JobSummary } from './recursive/JobSummary';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
}

export const ModalRecursiveRemoveEncryption = ({
  isOpen,
  onClose,
  item,
}: Props) => {
  const { t } = useTranslation();
  const job = useRecursiveEncryptionJob({
    mode: 'decrypt',
    item,
    isOpen,
    onSuccess: () => {
      setTimeout(onClose, 1200);
    },
  });

  const title =
    item.type === ItemType.FOLDER
      ? t(
          'encryption.remove_modal.title_folder',
          'Remove encryption from folder "{{title}}"',
          { title: item.title },
        )
      : t(
          'encryption.remove_modal.title_file',
          'Remove encryption from file "{{title}}"',
          { title: item.title },
        );

  const busy =
    job.phase === 'discovering' ||
    job.phase === 'validating' ||
    job.phase === 'staging' ||
    job.phase === 'committing';

  const hasValidation = job.validationErrors.length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      closeOnClickOutside={!busy}
      size={ModalSize.LARGE}
      title={title}
      actions={
        <>
          <Button
            variant="bordered"
            onClick={() => {
              if (busy) job.cancel();
              onClose();
            }}
          >
            {busy
              ? t('common.cancel', 'Cancel')
              : t('common.close', 'Close')}
          </Button>
          {job.phase === 'ready' && (
            <Button
              color="error"
              onClick={() => job.confirm()}
              disabled={!job.canConfirm}
            >
              {t('encryption.remove_modal.confirm', 'Remove encryption')}
            </Button>
          )}
          {job.phase === 'failed' && job.failedCount > 0 && (
            <Button onClick={() => job.retry()}>
              {t('common.retry', 'Retry')}
            </Button>
          )}
        </>
      }
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          minHeight: '200px',
        }}
      >
        {job.phase === 'ready' && (
          <p style={{ margin: 0 }}>
            {t(
              'encryption.remove_modal.description',
              'The following files will be decrypted and stored in plain.',
            )}
          </p>
        )}

        <JobSummary
          phase={job.phase}
          total={job.totalProcessable}
          done={job.doneCount}
          skipped={job.skippedCount}
          failed={job.failedCount}
          mode="decrypt"
        />

        {hasValidation && (
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '4px',
              background: 'var(--c--theme--colors--danger-100, #fde8e8)',
            }}
          >
            <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
              {job.validationErrors.map((e, i) => (
                <li
                  key={i}
                  style={{
                    color: 'var(--c--theme--colors--danger-text, #c00)',
                  }}
                >
                  {e}
                </li>
              ))}
            </ul>
          </div>
        )}

        {job.topError && (
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '4px',
              background: 'var(--c--theme--colors--danger-100, #fde8e8)',
              color: 'var(--c--theme--colors--danger-text, #c00)',
            }}
          >
            {job.topError}
          </div>
        )}

        {job.rows.length > 0 && (
          <div
            style={{
              maxHeight: '320px',
              overflowY: 'auto',
              border:
                '1px solid var(--c--theme--colors--greyscale-200, #e5e7eb)',
              borderRadius: '4px',
              padding: '0 0.5rem',
            }}
          >
            {job.rows.map((r) => (
              <JobFileRow row={r} key={r.id} />
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
};
