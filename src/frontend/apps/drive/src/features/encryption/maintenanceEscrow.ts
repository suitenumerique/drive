/**
 * The maintenance escrow copy of an encryption root's key.
 *
 * When the encryption service runs the maintenance escrow, the vault returns,
 * next to the per-user wraps, the root key wrapped once more for the
 * maintenance key covering the root OWNER's organization. Drive stores it on
 * the root only: every nested key chains from the root's, so that one copy is
 * enough for that organization's custodians to recover the whole tree offline.
 *
 * The vault picks the maintenance key from the owner's email domain, which only
 * the encryption service knows: Drive names the owner (the root's creator) and
 * never chooses a key. A copy from a share of someone else's root (the backfill
 * below) would otherwise follow the sharer's organization.
 *
 * The copy is stored when the root is encrypted, or backfilled below for a root
 * that has none. A share returns one too, never stored: it changes neither the
 * root key nor its owner, so that copy is the stored one with other randomness.
 */
import { getDriver } from "@/features/config/Config";
import type { KeyChain } from "@/features/drivers/Driver";
import { fromBase64, toBase64 } from "@/features/encryption/recursive/binary";

// One attempt per root and page: every file opened in the tree reads the same
// key chain, and a root the vault produces no copy for would be retried forever.
const attempted = new Set<string>();

/**
 * Give a root encrypted before the escrow was enabled (or before its owner's
 * domain was covered) its copy: an empty share returns only that copy. Silent,
 * and never in the way of the opening that triggered it.
 */
export async function backfillMaintenanceCopy(
  keyChain: KeyChain,
): Promise<void> {
  const escrow = keyChain.maintenance_escrow;
  const vaultClient = window.__driveVaultClient;
  if (
    !vaultClient ||
    !escrow ||
    escrow.has_maintenance_key ||
    !escrow.can_store ||
    !escrow.owner_sub ||
    attempted.has(escrow.root_item_id)
  ) {
    return;
  }
  attempted.add(escrow.root_item_id);
  try {
    const { maintenanceKey } = await vaultClient.shareKeys(
      fromBase64(keyChain.encrypted_key_for_user),
      {},
      undefined,
      escrow.owner_sub,
    );
    // No copy: no escrow configured, or the owner's domain not covered.
    if (maintenanceKey) {
      await getDriver().storeMaintenanceKey(
        escrow.root_item_id,
        toBase64(maintenanceKey),
      );
    }
  } catch (error) {
    console.warn("[maintenanceEscrow] could not backfill the copy", error);
  }
}
