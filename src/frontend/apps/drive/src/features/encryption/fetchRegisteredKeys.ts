/**
 * Adapter over `vaultClient.fetchPublicKeys`, which returns the full
 * registry directory keyed by userId. Drive only ever needs the
 * encryption public key and its version, and only for users that
 * actually hold a published key — this collapses the directory back to
 * the two parallel maps Drive's call sites consume, preserving the
 * original semantics (users without an encryption key simply do not
 * appear in either map).
 */
export async function fetchRegisteredKeys(userIds: string[]): Promise<{
  publicKeys: Record<string, ArrayBuffer>;
  versions: Record<string, number>;
}> {
  const vaultClient = window.__driveVaultClient;
  if (!vaultClient) {
    throw new Error('Vault client not available');
  }
  const users = await vaultClient.fetchPublicKeys(userIds);
  const publicKeys: Record<string, ArrayBuffer> = {};
  const versions: Record<string, number> = {};
  for (const [id, u] of Object.entries(users)) {
    if (u.encryptionPublicKey) {
      publicKeys[id] = u.encryptionPublicKey;
      versions[id] = u.version;
    }
  }
  return { publicKeys, versions };
}
