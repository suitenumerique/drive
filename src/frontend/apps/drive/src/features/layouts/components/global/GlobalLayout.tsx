import { Auth } from "@/features/auth/Auth";
import { RecursiveEncryptProvider } from "@/features/encryption/RecursiveEncryptProvider";
import { VaultClientProvider } from "@/features/encryption/VaultClientProvider";

/**
 * This layout is used for the global contexts (auth, etc).
 */
export const GlobalLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <Auth>
      <VaultClientProvider>
        <RecursiveEncryptProvider>{children}</RecursiveEncryptProvider>
      </VaultClientProvider>
    </Auth>
  );
};
