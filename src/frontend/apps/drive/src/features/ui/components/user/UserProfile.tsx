import { UserMenu } from "@gouvfr-lasuite/ui-kit";
import { useAuth } from "@/features/auth/Auth";
import { logout } from "@/features/auth/Auth";
import { LanguagePickerUserMenu } from "@/features/layouts/components/header/Header";
import { LoginButton } from "@/features/auth/components/LoginButton";
import { useVaultClient } from "@/features/encryption/VaultClientProvider";
import { ModalEncryptionOnboarding } from "@/features/encryption/ModalEncryptionOnboarding";
import { ModalEncryptionSettings } from "@/features/encryption/ModalEncryptionSettings";
import { useState, useCallback } from "react";

export const UserProfile = () => {
  const { user } = useAuth();
  const { hasKeys } = useVaultClient();
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleEncryptionClick = useCallback(() => {
    // Close the react-aria popover via Escape key
    document.activeElement?.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );

    if (hasKeys) {
      setIsSettingsOpen(true);
    } else {
      setIsOnboardingOpen(true);
    }
  }, [hasKeys]);

  if (!user) {
    return <LoginButton />;
  }

  return (
    <>
      <UserMenu
        user={user}
        logout={logout}
        termOfServiceUrl="https://docs.numerique.gouv.fr/docs/8e298e03-c95f-44c7-be4a-ffb618af1854/"
        settingsCTA={handleEncryptionClick}
        actions={<LanguagePickerUserMenu />}
      />

      {isOnboardingOpen && (
        <ModalEncryptionOnboarding
          isOpen
          onClose={() => setIsOnboardingOpen(false)}
          onSuccess={() => setIsOnboardingOpen(false)}
        />
      )}
      {isSettingsOpen && (
        <ModalEncryptionSettings
          isOpen
          onClose={() => setIsSettingsOpen(false)}
        />
      )}
    </>
  );
};
