export {};

declare global {
  interface VaultClient {
    init(): Promise<void>;
    destroy(): void;
    setTheme(theme: string): void;
    setAuthContext(context: { suiteUserId: string }): void;
    hasKeys(): Promise<{ hasKeys: boolean }>;
    getPublicKey(): Promise<{ publicKey: ArrayBuffer }>;
    // Root creation: mint a new key and wrap it under each user's pubkey.
    //
    // Note on `optimizeMemory` (present on all four data-handling methods
    // below): defaults to `false` — safe behaviour, the SDK clones the
    // input buffer on its way to the vault and the vault clones the
    // result on its way back. Caller's input buffer stays valid. Set to
    // `true` ONLY on hot paths where the caller is happy to lose
    // ownership of the input buffer (transferred + detached) in
    // exchange for skipping two large-buffer copies. Keys / chain /
    // userId are never transferred regardless of this flag.
    encryptWithoutKey(
      data: ArrayBuffer,
      userPublicKeys: Record<string, ArrayBuffer>,
      options?: { optimizeMemory?: boolean }
    ): Promise<{
      encryptedContent: ArrayBuffer;
      encryptedKeys: Record<string, ArrayBuffer>;
    }>;
    // Nested creation: mint a new key and wrap it under the parent folder's
    // key (resolved from entry + chain).
    encryptNestedWithoutKey(
      data: ArrayBuffer,
      encryptedSymmetricKey: ArrayBuffer,
      encryptedKeyChain?: ArrayBuffer[],
      options?: { optimizeMemory?: boolean }
    ): Promise<{ encryptedContent: ArrayBuffer; wrappedKey: ArrayBuffer }>;
    // Encrypt with an existing key — purely symmetric. No mint, no wrap.
    encryptWithKey(
      data: ArrayBuffer,
      encryptedSymmetricKey: ArrayBuffer,
      encryptedKeyChain?: ArrayBuffer[],
      options?: { optimizeMemory?: boolean }
    ): Promise<{ encryptedData: ArrayBuffer }>;
    decryptWithKey(
      encryptedData: ArrayBuffer,
      encryptedSymmetricKey: ArrayBuffer,
      encryptedKeyChain?: ArrayBuffer[],
      options?: { optimizeMemory?: boolean }
    ): Promise<{ data: ArrayBuffer }>;
    shareKeys(
      encryptedSymmetricKey: ArrayBuffer,
      userPublicKeys: Record<string, ArrayBuffer>
    ): Promise<{ encryptedKeys: Record<string, ArrayBuffer> }>;
    computeKeyFingerprint(publicKey: ArrayBuffer): Promise<string>;
    formatFingerprint(fingerprint: string): string;
    fetchPublicKeys(
      userIds: string[]
    ): Promise<{ publicKeys: Record<string, ArrayBuffer> }>;
    checkFingerprints(
      userFingerprints: Record<string, string>,
      currentUserId?: string
    ): Promise<{
      results: Array<{
        userId: string;
        knownFingerprint: string | null;
        providedFingerprint: string;
        status: 'trusted' | 'refused' | 'unknown';
      }>;
    }>;
    acceptFingerprint(userId: string, fingerprint: string): Promise<void>;
    refuseFingerprint(userId: string, fingerprint: string): Promise<void>;
    getKnownFingerprints(): Promise<{
      fingerprints: Record<
        string,
        {
          fingerprint: string;
          status: 'trusted' | 'refused' | 'unknown';
        }
      >;
    }>;
    openOnboarding(container: HTMLElement): void;
    openBackup(container: HTMLElement): void;
    openRestore(container: HTMLElement): void;
    openDeviceTransfer(container: HTMLElement): void;
    openSettings(container: HTMLElement): void;
    closeInterface(): void;
    on<K extends string>(event: K, listener: (data: unknown) => void): void;
    off<K extends string>(event: K, listener: (data: unknown) => void): void;
  }

  interface Window {
    EncryptionClient: {
      VaultClient: new (options: {
        vaultUrl: string;
        interfaceUrl: string;
        timeout?: number;
        theme?: string;
        lang?: string;
      }) => VaultClient;
    };
    __driveVaultClient: VaultClient | null;
  }
}
