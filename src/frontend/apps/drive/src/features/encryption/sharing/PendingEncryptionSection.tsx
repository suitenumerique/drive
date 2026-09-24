import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Access } from "@/features/drivers/types";
import { useMutationAcceptEncryptionAccess } from "@/features/explorer/hooks/useMutationsAccesses";
import { fetchSubtreeEntryKey, wrapSubtreeKeyForUser } from "./wrapKeyForUser";
import { fetchRegisteredKeys } from "@/features/encryption/fetchRegisteredKeys";

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
      const entryKey = await fetchSubtreeEntryKey(itemId);
      const wrapped = await wrapSubtreeKeyForUser(entryKey, {
        sub: access.user.sub,
        email: access.user.email,
        name: access.user.full_name,
      });
      if (!wrapped) {
        // Race: the key probe said they had one but fetching just now
        // returned nothing. Surface a concrete message and remove the
        // button optimistically.
        setHasPublicKeyBySub((m) => ({ ...m, [access.user.sub]: false }));
        throw new Error(
          t(
            "share_modal.pending_encryption.no_public_key",
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
        encryption_public_key_version: wrapped.version,
      });
      // Invalidate the currently-viewed item's access cache too when
      // it differs from where the access lives — the modal is looking
      // at a different query key and otherwise wouldn't refresh.
      if (access.item.id !== itemId) {
        queryClient.invalidateQueries({
          queryKey: ["itemAccesses", itemId],
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

  const initials = (label: string) =>
    label
      .trim()
      .split(/[\s.@_-]+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "?";

  return (
    <div className="drive__encryption-pending">
      <p className="drive__encryption-pending__title">
        {t("share_modal.pending_encryption.section_title", "Action needed")}
      </p>
      <ul className="drive__encryption-pending__rows">
        {pending.map((access) => {
          const isBusy = inFlight.has(access.id);
          const error = errorByAccessId[access.id];
          const hasPublicKey = hasPublicKeyBySub[access.user.sub];
          // Treat "probing" as "don't show the button yet" to avoid a
          // flicker where Accept appears then disappears.
          const canAccept = hasPublicKey === true && !probing;
          const name = access.user.full_name || access.user.email;
          return (
            <li key={access.id} className="drive__encryption-pending__row">
              <div className="drive__encryption-pending__who">
                <span
                  className="drive__encryption-pending__avatar"
                  aria-hidden="true"
                >
                  {initials(name)}
                </span>
                <div className="drive__encryption-pending__text">
                  <p className="drive__encryption-pending__name" title={name}>
                    {name}
                  </p>
                  {access.user.email && access.user.full_name && (
                    <p
                      className="drive__encryption-pending__secondary"
                      title={access.user.email}
                    >
                      {access.user.email}
                    </p>
                  )}
                  {!canAccept && !probing && (
                    <p className="drive__encryption-pending__secondary">
                      {t(
                        "share_modal.pending_encryption.awaiting_their_onboarding",
                        "Waiting for them to enable encryption. You will be able to accept them once they have.",
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
              ) : (
                <span className="drive__encryption-pending__chip">
                  <Icon aria-hidden name="schedule" />
                  {t(
                    "share_modal.pending_encryption.pending_chip",
                    "Pending encryption",
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
