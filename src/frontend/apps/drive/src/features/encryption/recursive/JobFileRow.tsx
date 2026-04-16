import { useTranslation } from 'react-i18next';
import { FileJobRow as FileJobRowType } from './types';

export const JobFileRow = ({ row }: { row: FileJobRowType }) => {
  const { t } = useTranslation();

  const stateIcon = (() => {
    switch (row.state) {
      case 'pending':
        return (
          <span
            className="material-icons"
            style={{
              opacity: 0.5,
              color: 'var(--c--theme--colors--greyscale-500, #6b7280)',
            }}
          >
            schedule
          </span>
        );
      case 'running':
        return (
          <span
            className="material-icons"
            style={{
              animation: 'spin 1s linear infinite',
              color: 'var(--c--theme--colors--primary-600, #1668dd)',
            }}
          >
            sync
          </span>
        );
      case 'staged':
        return (
          <span
            className="material-icons"
            style={{ color: 'var(--c--theme--colors--primary-600, #1668dd)' }}
          >
            cloud_done
          </span>
        );
      case 'done':
        return (
          <span
            className="material-icons"
            style={{ color: 'var(--c--theme--colors--success-600, #0d8050)' }}
          >
            check_circle
          </span>
        );
      case 'skipped':
        return (
          <span
            className="material-icons"
            style={{ color: 'var(--c--theme--colors--greyscale-500, #6b7280)' }}
          >
            remove_circle_outline
          </span>
        );
      case 'failed':
        return (
          <span
            className="material-icons"
            style={{ color: 'var(--c--theme--colors--danger-600, #c00)' }}
          >
            error
          </span>
        );
    }
  })();

  const caption = (() => {
    if (row.state === 'failed' && row.error) return row.error;
    if (row.state === 'skipped' && row.skipReason === 'already_encrypted') {
      return t('encryption.row.already_encrypted', 'Already encrypted');
    }
    if (row.state === 'skipped' && row.skipReason === 'not_encrypted') {
      return t('encryption.row.not_encrypted', 'Not encrypted');
    }
    return row.path || null;
  })();

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.5rem 0.25rem',
        borderBottom:
          '1px solid var(--c--theme--colors--greyscale-100, #eee)',
      }}
    >
      <div style={{ flexShrink: 0 }}>{stateIcon}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            fontWeight: 500,
          }}
        >
          {row.title}
        </div>
        {caption && (
          <div
            style={{
              fontSize: '0.8rem',
              color:
                row.state === 'failed'
                  ? 'var(--c--theme--colors--danger-text, #c00)'
                  : 'var(--c--theme--colors--greyscale-600, #6b7280)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {caption}
          </div>
        )}
      </div>
    </div>
  );
};
