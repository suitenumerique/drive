import { Button } from '@gouvfr-lasuite/cunningham-react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Access } from '@/features/drivers/types';
import { useMutationAcceptEncryptionAccess } from '@/features/explorer/hooks/useMutationsAccesses';
import {
  fetchSubtreeEntryKey,
  wrapSubtreeKeyForUser,
} from './wrapKeyForUser';

interface Props {
  itemId: string;
  accesses: Access[];
}

/**
 * Lists users who were added to an encrypted item before their access
 * was finalized with a wrapped key (`is_pending_encryption`).
 *
 * Two distinct sub-states per row:
 *  - They HAVE a public key → Accept button is actionable. One click
 *    re-wraps the subtree key for them and PATCHes the access row.
 *  - They have NO public key yet → no Accept button. A disabled-looking
 *    hint explains we're waiting for *them* to complete their encryption
 *    onboarding before anyone can re-wrap the key. Surfacing this
 *    distinction prevents the "click Accept, get a cryptic error" loop
 *    and makes clear who owns the next step.
 *
 * Rendered inline above the regular ShareModal contents so the main
 * ui-kit access list stays untouched.
 */
export const PendingEncryptionSection = ({ itemId, accesses }: Props) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const acceptMutation = useMutationAcceptEncryptionAccess();
  const [inFlight, setInFlight] = useState<Set<string>>(new Set());
  const [errorByAccessId, setErrorByAccessId] = useState<
    Record<string, string>
  >({});
  // Known state of each pending user's public key: undefined = still
  // probing, true = they have one (Accept is actionable), false = they
  // haven't onboarded yet (Accept is suppressed).
  const [hasPublicKeyBySub, setHasPublicKeyBySub] = useState<
    Record<string, boolean>
  >({});
  const [probing, setProbing] = useState(true);

  const pending = useMemo(
    () => accesses.filter((a) => a.is_pending_encryption),
    [accesses],
  );
  const pendingSubsSignature = useMemo(
    () =>
      pending
        .map((a) => a.user.sub)
        .sort()
        .join(','),
    [pending],
  );

  useEffect(() => {
    if (pending.length === 0) {
      setProbing(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setProbing(true);
      const vaultClient = window.__driveVaultClient;
      if (!vaultClient) {
        // Without the vault we can't probe; leave entries undefined so
        // the row falls back to "waiting for their onboarding" wording.
        if (!cancelled) setProbing(false);
        return;
      }
      const subs = pending
        .map((a) => a.user.sub)
        .filter((s): s is string => !!s);
      if (subs.length === 0) {
        if (!cancelled) setProbing(false);
        return;
      }
      try {
        const { publicKeys } = await vaultClient.fetchPublicKeys(subs);
        if (cancelled) return;
        const next: Record<string, boolean> = {};
        for (const sub of subs) {
          next[sub] = !!publicKeys[sub];
        }
        setHasPublicKeyBySub(next);
      } catch {
        // Probe failed; leave map empty → each row shows the "waiting
        // for their onboarding" wording. That's the safer default than
        // offering a button that would 400 on the accept endpoint.
      } finally {
        if (!cancelled) setProbing(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // pendingSubsSignature intentionally used instead of `pending` itself
    // to avoid re-firing on unrelated Access array identity changes.
  }, [pendingSubsSignature]); // eslint-disable-line react-hooks/exhaustive-deps

  if (pending.length === 0) {
    return null;
  }

  const handleAccept = async (access: Access) => {
    setInFlight((prev) => new Set(prev).add(access.id));
    setErrorByAccessId((prev) => {
      const copy = { ...prev };
      delete copy[access.id];
      return copy;
    });
    try {
      const entryKey = await fetchSubtreeEntryKey(itemId);
      const wrapped = await wrapSubtreeKeyForUser(entryKey, access.user.sub);
      if (!wrapped) {
        // Race: the key probe said they had one but fetching just now
        // returned nothing. Surface a concrete message and remove the
        // button optimistically.
        setHasPublicKeyBySub((m) => ({ ...m, [access.user.sub]: false }));
        throw new Error(
          t(
            'share_modal.pending_encryption.no_public_key',
            "This user still hasn't completed their encryption onboarding.",
          ),
        );
      }
      // The ItemAccess row physically lives on the encryption root
      // (the outermost ancestor where the share was granted), NOT on
      // the currently-viewed item. When the user opens the share modal
      // on a file inside a shared encrypted folder, the file's access
      // list contains INHERITED rows whose `item.id` points to the
      // folder. The PATCH URL must target that owning item — otherwise
      // `ItemAccessViewSet.filter_queryset` restricts the queryset to
      // accesses directly attached to the URL item and returns 404.
      await acceptMutation.mutateAsync({
        itemId: access.item.id,
        accessId: access.id,
        encrypted_item_symmetric_key_for_user: wrapped.wrappedKeyBase64,
        encryption_public_key_fingerprint: wrapped.fingerprint,
      });
      // Invalidate the currently-viewed item's access cache too when
      // it differs from where the access lives — the modal is looking
      // at a different query key and otherwise wouldn't refresh.
      if (access.item.id !== itemId) {
        queryClient.invalidateQueries({
          queryKey: ['itemAccesses', itemId],
        });
      }
    } catch (err) {
      setErrorByAccessId((prev) => ({
        ...prev,
        [access.id]: err instanceof Error ? err.message : String(err),
      }));
    } finally {
      setInFlight((prev) => {
        const copy = new Set(prev);
        copy.delete(access.id);
        return copy;
      });
    }
  };

  return (
    <div
      style={{
        margin: '0.5rem 0 1rem',
        padding: '0.75rem',
        border: '1px solid var(--c--theme--colors--warning-300, #ffd591)',
        borderRadius: 4,
        background: 'var(--c--theme--colors--warning-050, #fffbf0)',
      }}
    >
      <div
        style={{
          fontWeight: 600,
          marginBottom: '0.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <span
          className="material-icons"
          style={{
            fontSize: 18,
            color: 'var(--c--theme--colors--warning-600, #b15600)',
          }}
        >
          hourglass_empty
        </span>
        {t(
          'share_modal.pending_encryption.title',
          'Users pending encryption access ({{count}})',
          { count: pending.length },
        )}
      </div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {pending.map((access) => {
          const isBusy = inFlight.has(access.id);
          const error = errorByAccessId[access.id];
          const hasPublicKey = hasPublicKeyBySub[access.user.sub];
          // Treat "probing" as "don't show the button yet" to avoid a
          // flicker where Accept appears then disappears.
          const canAccept = hasPublicKey === true && !probing;
          return (
            <li
              key={access.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.4rem 0',
                gap: '0.5rem',
                flexWrap: 'wrap',
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500 }}>
                  {access.user.full_name || access.user.email}
                </div>
                {access.user.email && access.user.full_name && (
                  <div
                    style={{
                      fontSize: '0.85rem',
                      color:
                        'var(--c--contextuals--content--semantic--neutral--tertiary)',
                    }}
                  >
                    {access.user.email}
                  </div>
                )}
                {!canAccept && !probing && (
                  <div
                    style={{
                      fontSize: '0.85rem',
                      color:
                        'var(--c--contextuals--content--semantic--neutral--tertiary)',
                      marginTop: '0.25rem',
                    }}
                  >
                    {t(
                      'share_modal.pending_encryption.awaiting_their_onboarding',
                      "Waiting for this user to complete their encryption onboarding. You'll be able to accept them once they have.",
                    )}
                  </div>
                )}
                {error && (
                  <div
                    style={{
                      fontSize: '0.85rem',
                      color: 'var(--c--theme--colors--danger-600, #c9191e)',
                      marginTop: '0.25rem',
                    }}
                  >
                    {error}
                  </div>
                )}
              </div>
              {canAccept && (
                <Button
                  size="small"
                  onClick={() => handleAccept(access)}
                  disabled={isBusy}
                >
                  {isBusy
                    ? t(
                        'share_modal.pending_encryption.accepting',
                        'Accepting…',
                      )
                    : t('share_modal.pending_encryption.accept', 'Accept')}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};
