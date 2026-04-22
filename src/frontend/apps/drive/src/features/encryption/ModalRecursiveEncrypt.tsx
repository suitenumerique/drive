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

export const ModalRecursiveEncrypt = ({ isOpen, onClose, item }: Props) => {
  const { t } = useTranslation();
  const job = useRecursiveEncryptionJob({
    mode: 'encrypt',
    item,
    isOpen,
    onSuccess: () => {
      setTimeout(onClose, 1200);
    },
  });

  const title =
    item.type === ItemType.FOLDER
      ? t('encryption.encrypt_modal.title_folder', 'Encrypt folder "{{title}}"', {
          title: item.title,
        })
      : t('encryption.encrypt_modal.title_file', 'Encrypt file "{{title}}"', {
          title: item.title,
        });

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
              onClick={() => job.confirm()}
              disabled={!job.canConfirm}
            >
              {t('encryption.encrypt_modal.confirm', 'Encrypt')}
            </Button>
          )}
          {job.phase === 'failed' && (
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
        {item.type === ItemType.FOLDER && job.phase === 'ready' && (
          <p style={{ margin: 0 }}>
            {t(
              'encryption.encrypt_modal.description_folder',
              'The following items will be encrypted. Subfolders are processed recursively. Once encrypted, contents can only be accessed by users with encryption keys.',
            )}
          </p>
        )}

        {job.pendingUserCount > 0 &&
          (job.phase === 'ready' || job.phase === 'validating') && (
            <div
              style={{
                padding: '0.75rem',
                borderRadius: '4px',
                background: 'var(--c--theme--colors--warning-050, #fffbf0)',
                border:
                  '1px solid var(--c--theme--colors--warning-400, #ffb860)',
                display: 'flex',
                gap: '0.6rem',
                alignItems: 'flex-start',
              }}
            >
              <span
                className="material-icons"
                style={{
                  fontSize: 22,
                  color: 'var(--c--theme--colors--warning-700, #8f4400)',
                  lineHeight: 1,
                }}
              >
                warning_amber
              </span>
              <div style={{ fontSize: '0.9rem', lineHeight: 1.4 }}>
                <div style={{ fontWeight: 600, marginBottom: '0.2rem' }}>
                  {t(
                    'encryption.encrypt_modal.pending_users_title',
                    '{{count}} collaborator(s) haven’t completed encryption onboarding',
                    { count: job.pendingUserCount },
                  )}
                </div>
                <div>
                  {t(
                    'encryption.encrypt_modal.pending_users_body',
                    'If you proceed, they will still see this folder in their listings but will not be able to open its contents until they complete their onboarding AND another user accepts them from the share dialog.',
                  )}
                </div>
              </div>
            </div>
          )}

        <JobSummary
          phase={job.phase}
          total={job.totalProcessable}
          done={job.doneCount}
          skipped={job.skippedCount}
          failed={job.failedCount}
          mode="encrypt"
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

        {job.rows.length > 0 && job.rows.length <= 50 && (
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
        {job.rows.length > 50 && (
          <p
            style={{
              margin: 0,
              fontSize: '0.85rem',
              color: 'var(--c--theme--colors--greyscale-600, #6b7280)',
            }}
          >
            {t(
              'encryption.encrypt_modal.large_set',
              '{{count}} items in this folder. Per-item progress is hidden for large jobs — see the summary above.',
              { count: job.rows.length },
            )}
            {job.failedCount > 0 &&
              ' ' +
                t(
                  'encryption.encrypt_modal.large_set_failures',
                  '{{count}} failed.',
                  { count: job.failedCount },
                )}
          </p>
        )}
      </div>
    </Modal>
  );
};
