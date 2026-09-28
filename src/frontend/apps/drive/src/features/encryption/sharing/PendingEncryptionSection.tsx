import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon, UserAvatar } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { useEffect, useMemo, useState } from "react";
import { Access } from "@/features/drivers/types";
import { fetchRegisteredKeys } from "@/features/encryption/fetchRegisteredKeys";
import { useAcceptPendingMembers } from "./acceptPendingMembers";

interface Props {
  itemId: string;
  accesses: Access[];
  canAccept: boolean;
}

/**
 * Lists users who were added to an encrypted item before their access
 * was finalized with a wrapped key (`is_pending_encryption`).
 *
 * Two distinct sub-states per row:
 *  - They HAVE a public key → Accept button is actionable. One click
 *    re-wraps the subtree key for them and PATCHes the access row.
 *  - They have NO public key yet → no Accept button, a "Waiting for
 *    encryption" chip; one line under the heading explains it for every
 *    such row. This prevents the "click Accept, get a cryptic error" loop.
 *
 * Rendered inline above the regular ShareModal contents so the main
 * ui-kit access list stays untouched.
 */
export const PendingEncryptionSection = ({
  itemId,
  accesses,
  canAccept: mayAccept,
}: Props) => {
  const { t } = useTranslation();
  const acceptPendingMembers = useAcceptPendingMembers();
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
        .join(","),
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
        const { publicKeys } = await fetchRegisteredKeys(subs);
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
  }, [pendingSubsSignature]);

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
      const { accepted, notReady } = await acceptPendingMembers(itemId, [
        access,
      ]);
      if (notReady.length > 0 || accepted.length === 0) {
        setHasPublicKeyBySub((m) => ({ ...m, [access.user.sub]: false }));
        throw new Error(
          t(
            "share_modal.pending_encryption.no_public_key",
            "This user still hasn't completed their encryption onboarding.",
          ),
        );
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

  // Treat "probing" as "don't show the button yet" to avoid a flicker where
  // Accept appears then disappears.
  const canAcceptAccess = (access: Access) =>
    mayAccept && hasPublicKeyBySub[access.user.sub] === true && !probing;
  const someoneWaiting =
    !probing &&
    pending.some((access) => hasPublicKeyBySub[access.user.sub] !== true);

  return (
    <div className="c__share-modal__link-settings drive__encryption-pending">
      <div className="drive__encryption-pending__heading">
        <p className="c__share-modal__link-settings__title drive__encryption-pending__title">
          {t("share_modal.pending_encryption.section_title", "Action needed")}
        </p>
        {someoneWaiting && (
          <p className="drive__encryption-pending__hint">
            {t(
              "share_modal.pending_encryption.waiting_hint",
              "Members who have not enabled encryption yet get access once they do.",
            )}
          </p>
        )}
      </div>
      <ul className="drive__encryption-pending__rows">
        {pending.map((access) => {
          const isBusy = inFlight.has(access.id);
          const error = errorByAccessId[access.id];
          const hasPublicKey = hasPublicKeyBySub[access.user.sub] === true;
          const canAccept = canAcceptAccess(access);
          const name = access.user.full_name || access.user.email;
          return (
            <li key={access.id} className="drive__encryption-pending__row">
              <div className="drive__encryption-pending__who">
                {/* The design system's avatar, as in the member list, so the
                    same person gets the same colour in both. */}
                <UserAvatar fullName={name} size="small" />
                <div className="drive__encryption-pending__text">
                  <p
                    className="c__user-row__name drive__encryption-pending__name"
                    title={name}
                  >
                    {name}
                  </p>
                  {access.user.email && access.user.full_name && (
                    <p
                      className="c__user-row__email drive__encryption-pending__secondary"
                      title={access.user.email}
                    >
                      {access.user.email}
                    </p>
                  )}
                  {/* The Accept button already says it; a viewer who cannot accept
                      gets the status instead. */}
                  {hasPublicKey && !probing && !canAccept && (
                    <p className="drive__encryption-pending__enabled">
                      <Icon aria-hidden name="verified_user" />
                      {t(
                        "share_modal.pending_encryption.encryption_enabled",
                        "Encryption enabled",
                      )}
                    </p>
                  )}
                  {error && (
                    <p className="drive__encryption-pending__error">{error}</p>
                  )}
                </div>
              </div>
              {canAccept ? (
                <Button
                  size="small"
                  variant="bordered"
                  onClick={() => handleAccept(access)}
                  disabled={isBusy}
                >
                  {isBusy
                    ? t(
                        "share_modal.pending_encryption.accepting",
                        "Accepting…",
                      )
                    : t("share_modal.pending_encryption.accept", "Accept")}
                </Button>
              ) : hasPublicKey ? null : (
                <span
                  className="drive__encryption-pending__chip"
                  title={t(
                    "share_modal.pending_encryption.waiting_chip_hint",
                    "Waiting for them to enable encryption",
                  )}
                >
                  <Icon aria-hidden name="schedule" />
                  {t(
                    "share_modal.pending_encryption.waiting_chip",
                    "Waiting for encryption",
                  )}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};
