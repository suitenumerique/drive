import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/features/auth/Auth';
import {
  MISSING_KEYS_EVENT,
  MissingEncryptionKeysModal,
} from './MissingEncryptionKeysModal';
import { ModalEncryptionOnboarding } from './ModalEncryptionOnboarding';

const VAULT_URL = process.env.NEXT_PUBLIC_VAULT_URL ?? 'http://localhost:7201';
const INTERFACE_URL =
  process.env.NEXT_PUBLIC_INTERFACE_URL ?? 'http://localhost:7202';

export interface VaultClientContextValue {
  client: VaultClient | null;
  isReady: boolean;
  isLoading: boolean;
  error: string | null;
  hasKeys: boolean | null;
  publicKey: ArrayBuffer | null;
  refreshKeyState: () => Promise<void>;
  /**
   * Open the "missing encryption keys" modal — the consent step that lets
   * the user decline or jump into onboarding to generate / restore their
   * key pair. Wired to a window-level event (`vault:missing-keys`) so any
   * non-React caller (e.g. the global mutation error handler) can trigger
   * it via `window.dispatchEvent(new CustomEvent('vault:missing-keys'))`.
   */
  promptMissingKeys: () => void;
  /**
   * Open the onboarding flow directly — used by callers that have already
   * surfaced their own context to the user (e.g. the in-viewer panel) and
   * want to skip the consent step.
   */
  openEncryptionOnboarding: () => void;
}

const VaultClientContext = createContext<VaultClientContextValue>({
  client: null,
  isReady: false,
  isLoading: true,
  error: null,
  hasKeys: null,
  publicKey: null,
  refreshKeyState: async () => {},
  promptMissingKeys: () => {},
  openEncryptionOnboarding: () => {},
});

function loadClientScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.EncryptionClient?.VaultClient) {
      resolve();
      return;
    }

    const existing = document.querySelector(
      `script[src="${VAULT_URL}/client.js"]`
    );
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () =>
        reject(new Error('Failed to load encryption client SDK'))
      );
      return;
    }

    const script = document.createElement('script');
    script.src = `${VAULT_URL}/client.js`;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () =>
      reject(new Error('Failed to load encryption client SDK'));
    document.head.appendChild(script);
  });
}

export function VaultClientProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user } = useAuth();
  const { i18n } = useTranslation();
  const clientRef = useRef<VaultClient | null>(null);
  const [clientInitialized, setClientInitialized] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasKeys, setHasKeys] = useState<boolean | null>(null);
  const [publicKey, setPublicKey] = useState<ArrayBuffer | null>(null);
  const initRef = useRef(false);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    let destroyed = false;

    async function init() {
      try {
        await loadClientScript();
        if (destroyed) return;

        const client = new window.EncryptionClient.VaultClient({
          vaultUrl: VAULT_URL,
          interfaceUrl: INTERFACE_URL,
          lang: i18n.language,
        });

        clientRef.current = client;
        window.__driveVaultClient = client;

        client.on('onboarding:complete', () => {
          setHasKeys(true);
          client
            .getPublicKey()
            .then(({ publicKey: pk }) => setPublicKey(pk))
            .catch(() => {});
        });

        client.on('keys-changed', () => {
          client
            .hasKeys()
            .then(({ hasKeys: exists }) => {
              setHasKeys(exists);
              if (exists) {
                client
                  .getPublicKey()
                  .then(({ publicKey: pk }) => setPublicKey(pk))
                  .catch(() => {});
              }
            })
            .catch(() => {});
        });

        client.on('keys-destroyed', () => {
          setHasKeys(false);
          setPublicKey(null);
        });

        await client.init();

        if (destroyed) {
          client.destroy();
        } else {
          setClientInitialized(true);
        }
      } catch (err) {
        if (!destroyed) {
          setError((err as Error).message);
          setIsLoading(false);
        }
      }
    }

    void init();

    return () => {
      destroyed = true;
      if (clientRef.current) {
        clientRef.current.destroy();
        clientRef.current = null;
        window.__driveVaultClient = null;
      }
    };
  }, []);

  useEffect(() => {
    const client = clientRef.current;
    if (!client || !clientInitialized || !user?.sub) {
      return;
    }

    let cancelled = false;

    async function setupAuth() {
      if (cancelled || !client) return;

      client.setAuthContext({ suiteUserId: user!.sub! });
      setIsLoading(true);

      try {
        const { hasKeys: exists } = await client.hasKeys();
        setHasKeys(exists);

        if (exists) {
          const { publicKey: pk } = await client.getPublicKey();
          setPublicKey(pk);
        }

        setIsReady(true);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setIsLoading(false);
      }
    }

    void setupAuth();

    return () => {
      cancelled = true;
    };
  }, [clientInitialized, user?.sub]);

  const [missingKeysModalOpen, setMissingKeysModalOpen] = useState(false);
  const [onboardingFromPromptOpen, setOnboardingFromPromptOpen] =
    useState(false);

  const promptMissingKeys = useCallback(() => {
    // Skip when onboarding is already in progress — surfacing the consent
    // step on top of it would just be noise.
    if (onboardingFromPromptOpen) return;
    setMissingKeysModalOpen(true);
  }, [onboardingFromPromptOpen]);

  const openEncryptionOnboarding = useCallback(() => {
    setMissingKeysModalOpen(false);
    setOnboardingFromPromptOpen(true);
  }, []);

  // Bridge for non-React callers (mutation onError, deep helpers): listen for
  // a global window event and open the consent modal. Idempotent — repeated
  // dispatches while the modal is already open are no-ops.
  useEffect(() => {
    const handler = () => promptMissingKeys();
    window.addEventListener(MISSING_KEYS_EVENT, handler);
    return () => window.removeEventListener(MISSING_KEYS_EVENT, handler);
  }, [promptMissingKeys]);

  const refreshKeyState = useCallback(async () => {
    const client = clientRef.current;
    if (!client) return;

    try {
      const { hasKeys: exists } = await client.hasKeys();
      setHasKeys(exists);

      if (exists) {
        const { publicKey: pk } = await client.getPublicKey();
        setPublicKey(pk);
      } else {
        setPublicKey(null);
      }
    } catch {
      // Vault not available
    }
  }, []);

  return (
    <VaultClientContext.Provider
      value={{
        client: isReady ? clientRef.current : null,
        isReady,
        isLoading,
        error,
        hasKeys,
        publicKey,
        refreshKeyState,
        promptMissingKeys,
        openEncryptionOnboarding,
      }}
    >
      {children}
      <MissingEncryptionKeysModal
        isOpen={missingKeysModalOpen}
        onClose={() => setMissingKeysModalOpen(false)}
        onSetUp={openEncryptionOnboarding}
      />
      {onboardingFromPromptOpen && (
        <ModalEncryptionOnboarding
          isOpen
          onClose={() => setOnboardingFromPromptOpen(false)}
          onSuccess={() => setOnboardingFromPromptOpen(false)}
        />
      )}
    </VaultClientContext.Provider>
  );
}

export const useVaultClient = (): VaultClientContextValue =>
  useContext(VaultClientContext);
