import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * A decryption failure with this message text almost always means the
 * file was encrypted against a PREVIOUS public key of the current user
 * (e.g. they reset their keys, or restored from a different device and
 * got new keys generated). The ciphertext can still be opened by anyone
 * who holds the old key; the user themselves cannot, no matter what
 * they do locally. The fix is social: an owner/admin of the document
 * has to remove them from the access list and re-add them so the
 * symmetric key gets wrapped against the user's CURRENT public key.
 */
export const isWrongSecretKeyError = (
  err: Error | null | undefined
): boolean => {
  if (!err) return false;
  const msg = err.message?.toLowerCase() ?? '';
  return msg.includes('wrong secret key');
};

interface KeyMismatchPanelProps {
  /**
   * Fingerprint stored on the user's access row at share time (i.e.
   * the fingerprint of the key the file was actually encrypted for).
   * Comes from `item.encryption_public_key_fingerprint_for_user` on
   * Drive or `doc.accesses_fingerprints_per_user[currentUser.sub]` on
   * Docs. Optional — if absent, only the current key is shown.
   */
  shareTimeFingerprint?: string | null;
}

/**
 * Friendly panel shown when `isWrongSecretKeyError` is true. Explains
 * the situation and surfaces BOTH the fingerprint the file was
 * encrypted for (stored at share time) and the user's current key's
 * fingerprint, so they can see the mismatch concretely and give the
 * new fingerprint to whoever re-adds them.
 */
export const KeyMismatchPanel = ({
  shareTimeFingerprint,
}: KeyMismatchPanelProps = {}) => {
  const { t } = useTranslation();
  const [currentFingerprint, setCurrentFingerprint] = useState<string | null>(
    null
  );

  useEffect(() => {
    const vault = window.__driveVaultClient;
    if (!vault) return;
    let cancelled = false;
    (async () => {
      try {
        const { publicKey } = await vault.getPublicKey();
        const raw = await vault.computeKeyFingerprint(publicKey);
        const formatted = vault.formatFingerprint(raw);
        if (!cancelled) setCurrentFingerprint(formatted);
      } catch {
        // Ignore — we just won't show the fingerprint row.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const formatShareTime = (() => {
    const vault = window.__driveVaultClient;
    if (!shareTimeFingerprint) return null;
    if (!vault) return shareTimeFingerprint;
    try {
      return vault.formatFingerprint(shareTimeFingerprint);
    } catch {
      return shareTimeFingerprint;
    }
  })();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        gap: '16px',
        padding: '24px',
        textAlign: 'center',
        maxWidth: '520px',
        margin: '0 auto',
      }}
    >
      <span
        className="material-icons"
        style={{
          fontSize: '48px',
          color: 'var(--c--theme--colors--warning-600, #b15600)',
        }}
      >
        key_off
      </span>
      <span style={{ fontWeight: 600 }}>
        {t(
          'explorer.encrypted.key_mismatch.title',
          'This file was encrypted with a different key'
        )}
      </span>
      <span
        style={{
          fontSize: '14px',
          color: 'var(--c--contextuals--content--semantic--neutral--tertiary)',
          lineHeight: 1.5,
        }}
      >
        {t(
          'explorer.encrypted.key_mismatch.body',
          'The file was encrypted for you at a time when you were using a different encryption key — possibly before you reset your keys or switched device without restoring a backup. Your current key can no longer decrypt it. Ask an owner or administrator of this file to remove you from the access list and add you back so it gets re-encrypted for your current key.'
        )}
      </span>
      {(formatShareTime || currentFingerprint) && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            fontSize: '13px',
            color:
              'var(--c--contextuals--content--semantic--neutral--tertiary)',
          }}
        >
          {formatShareTime && (
            <div>
              {t(
                'explorer.encrypted.key_mismatch.share_time_fingerprint_label',
                'Fingerprint at the time it was shared with you:'
              )}{' '}
              <code
                style={{
                  fontFamily: 'monospace',
                  background: 'var(--c--theme--colors--greyscale-100, #f4f4f5)',
                  padding: '2px 6px',
                  borderRadius: '3px',
                }}
              >
                {formatShareTime}
              </code>
            </div>
          )}
          {currentFingerprint && (
            <div>
              {t(
                'explorer.encrypted.key_mismatch.fingerprint_label',
                'Your current key fingerprint:'
              )}{' '}
              <code
                style={{
                  fontFamily: 'monospace',
                  background: 'var(--c--theme--colors--greyscale-100, #f4f4f5)',
                  padding: '2px 6px',
                  borderRadius: '3px',
                }}
              >
                {currentFingerprint}
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
