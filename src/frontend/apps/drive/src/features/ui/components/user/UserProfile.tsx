import { UserMenu, UserMenuItem } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/features/auth/Auth";
import { logout } from "@/features/auth/Auth";
import { LanguagePickerUserMenu } from "@/features/layouts/components/header/Header";
import { LoginButton } from "@/features/auth/components/LoginButton";
import { useVaultClient } from "@/features/encryption/VaultClientProvider";
import { ModalEncryptionOnboarding } from "@/features/encryption/ModalEncryptionOnboarding";
import { ModalEncryptionSettings } from "@/features/encryption/ModalEncryptionSettings";
import { useState, useCallback } from "react";

export const UserProfile = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { hasKeys, isEnabled: isEncryptionEnabled } = useVaultClient();
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
        actions={
          <>
            {isEncryptionEnabled && (
              <UserMenuItem
                label={
                  hasKeys
                    ? t("encryption.user_menu.settings", "Encryption settings")
                    : t("encryption.user_menu.enable", "Enable encryption")
                }
                icon="verified_user"
                onClick={handleEncryptionClick}
              />
            )}
            <LanguagePickerUserMenu />
          </>
        }
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
