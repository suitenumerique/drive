import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { fetchRegisteredKeys } from "@/features/encryption/fetchRegisteredKeys";
import { EncryptionState } from "./EncryptionLayout";

/**
 * True when the SDK threw a `VaultError` carrying the
 * `WRONG_SECRET_KEY` code. In drive this almost always means the file
 * was encrypted against a PREVIOUS public key of the current user
 * (e.g. they reset their keys, or restored from a different device and
 * got new keys generated): the wrapped symmetric key was sealed
 * against their old pubkey, so the AEAD verification fails. The fix is
 * social — an owner/admin of the document has to remove them from the
 * access list and re-add them so the symmetric key gets wrapped
 * against the user's CURRENT public key.
 */
export const isWrongSecretKeyError = (
  err: Error | null | undefined,
): boolean => {
  if (!err) return false;
  return (err as VaultError).code === "WRONG_SECRET_KEY";
};

interface KeyMismatchPanelProps {
  /**
   * Encryption public key VERSION stored on the user's access row at
   * share time (i.e. the version of the key the file was actually
   * encrypted for). Comes from
   * `item.encryption_public_key_version_for_user` on Drive. Optional —
   * if absent, only the current version is shown. This is the per-access
   * staleness marker: when it lags behind the user's current version the
   * access needs re-wrapping.
   */
  shareTimeVersion?: number | null;
}

/**
 * Shown when `isWrongSecretKeyError` is true. Explains the situation and
 * surfaces BOTH the key version the file was encrypted for (stored at share
 * time) and the user's CURRENT key version, so the staleness is concrete: the
 * access was wrapped for version N of their key, their current version is M,
 * so a re-encryption is needed.
 */
export const KeyMismatchPanel = ({
  shareTimeVersion,
}: KeyMismatchPanelProps = {}) => {
  const { t } = useTranslation();
  const [currentVersion, setCurrentVersion] = useState<number | null>(null);

  useEffect(() => {
    const vault = window.__driveVaultClient;
    if (!vault) return;
    let cancelled = false;
    (async () => {
      try {
        const sub = vault.getAuthContext()?.suiteUserId;
        if (!sub) return;
        const { versions } = await fetchRegisteredKeys([sub]);
        if (!cancelled) setCurrentVersion(versions[sub] ?? null);
      } catch {
        // Ignore — we just won't show the current version row.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const hasShareTimeVersion =
    shareTimeVersion !== undefined && shareTimeVersion !== null;
  const hasCurrentVersion = currentVersion !== null;

  return (
    <EncryptionState
      title={t(
        "explorer.encrypted.key_mismatch.title",
        "This file was encrypted with a different key",
      )}
      description={t(
        "explorer.encrypted.key_mismatch.body",
        "The file was encrypted for you at a time when you were using a different encryption key — possibly before you reset your keys or switched device without restoring a backup. Your current key can no longer decrypt it. Ask an owner or administrator of this file to remove you from the access list and add you back so it gets re-encrypted for your current key.",
      )}
    >
      {(hasShareTimeVersion || hasCurrentVersion) && (
        <div className="drive__encryption-state__versions">
          {hasShareTimeVersion && (
            <div>
              {t(
                "explorer.encrypted.key_mismatch.share_time_version_label",
                "Key version at the time it was shared with you:",
              )}{" "}
              <code>{shareTimeVersion}</code>
            </div>
          )}
          {hasCurrentVersion && (
            <div>
              {t(
                "explorer.encrypted.key_mismatch.current_version_label",
                "Your current key version:",
              )}{" "}
              <code>{currentVersion}</code>
            </div>
          )}
        </div>
      )}
    </EncryptionState>
  );
};
