import { useTranslation } from 'react-i18next';
import { JobPhase } from './types';

type Props = {
  phase: JobPhase;
  total: number;
  done: number;
  skipped: number;
  failed: number;
  mode: 'encrypt' | 'decrypt';
};

export const JobSummary = ({
  phase,
  total,
  done,
  skipped,
  failed,
  mode,
}: Props) => {
  const { t } = useTranslation();

  const actionLabel =
    mode === 'encrypt'
      ? t('encryption.summary.encrypting', 'Encrypting')
      : t('encryption.summary.decrypting', 'Decrypting');

  const bar = (pct: number) => (
    <div
      style={{
        height: '6px',
        borderRadius: '3px',
        background: 'var(--c--theme--colors--greyscale-100, #eee)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${Math.max(0, Math.min(100, pct))}%`,
          height: '100%',
          background: 'var(--c--theme--colors--primary-500, #2563eb)',
          transition: 'width 0.2s ease-out',
        }}
      />
    </div>
  );

  let headline: string;
  let pct = 0;

  switch (phase) {
    case 'discovering':
      headline = t('encryption.summary.discovering', 'Discovering files…');
      break;
    case 'validating':
      headline = t('encryption.summary.validating', 'Validating…');
      break;
    case 'ready':
      headline = t(
        'encryption.summary.ready',
        '{{total}} item(s) to process, {{skipped}} skipped',
        { total, skipped },
      );
      break;
    case 'staging':
      headline = `${actionLabel} ${done} / ${total}${
        skipped > 0
          ? ` — ${t('encryption.summary.skipped_short', '{{n}} skipped', { n: skipped })}`
          : ''
      }`;
      pct = total > 0 ? (done / total) * 100 : 0;
      break;
    case 'committing':
      headline = t('encryption.summary.committing', 'Finalizing…');
      pct = 100;
      break;
    case 'success':
      headline =
        mode === 'encrypt'
          ? t(
              'encryption.summary.success_encrypt',
              '{{n}} item(s) encrypted',
              { n: done },
            )
          : t(
              'encryption.summary.success_decrypt',
              '{{n}} item(s) decrypted',
              { n: done },
            );
      pct = 100;
      break;
    case 'failed':
      headline =
        failed > 0
          ? t(
              'encryption.summary.failed',
              'Failed — {{n}} item(s) in error, no changes applied',
              { n: failed },
            )
          : t('encryption.summary.failed_generic', 'Operation failed');
      break;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ fontWeight: 600 }}>{headline}</div>
      {(phase === 'staging' || phase === 'committing' || phase === 'success') &&
        bar(pct)}
    </div>
  );
};
