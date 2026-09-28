import {
  DropdownMenu,
  Icon,
  IconSize,
  useDropdownMenu,
  UserMenu,
  Button,
} from "@gouvfr-lasuite/ui-components";
import { useAuth } from "@/features/auth/Auth";
import { logout } from "@/features/auth/Auth";
import { LanguagePickerUserMenu } from "@/features/layouts/components/header/Header";
import { LANGUAGES } from "@/features/i18n/conf";
import { AnonymousCTA } from "../anonymous-cta/AnonymousCTA";
import { useTranslation } from "react-i18next";
import { useClipboard } from "@/hooks/useCopyToClipboard";
import { useVaultClient } from "@/features/encryption/VaultClientProvider";
import { ModalEncryptionOnboarding } from "@/features/encryption/ModalEncryptionOnboarding";
import { ModalEncryptionSettings } from "@/features/encryption/ModalEncryptionSettings";
import { useCallback, useState } from "react";

export const UserProfile = () => {
  const { user } = useAuth();
  const { hasKeys, isEnabled: isEncryptionEnabled } = useVaultClient();
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleEncryptionClick = useCallback(() => {
    // The user menu is a react-aria popover with no close handle exposed:
    // Escape is the way to dismiss it before our modal opens.
    document.activeElement?.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );

    if (hasKeys) {
      setIsSettingsOpen(true);
    } else {
      setIsOnboardingOpen(true);
    }
  }, [hasKeys]);

  return (
    <div className="user-profile">
      {user ? (
        <>
          <UserMenu
            user={user}
            logout={logout}
            termOfServiceUrl="https://docs.numerique.gouv.fr/docs/8e298e03-c95f-44c7-be4a-ffb618af1854/"
            appSettingsCTA={
              isEncryptionEnabled ? handleEncryptionClick : undefined
            }
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
      ) : (
        <>
          <AnonymousDropdownMenu />
          <AnonymousCTA />
        </>
      )}
    </div>
  );
};

const AnonymousDropdownMenu = () => {
  const { isOpen, setIsOpen } = useDropdownMenu();
  const { t, i18n } = useTranslation();
  const copyToClipboard = useClipboard();

  return (
    <DropdownMenu
      isOpen={isOpen}
      onOpenChange={setIsOpen}
      options={[
        {
          icon: <Icon name="link" size={IconSize.SMALL} />,
          label: t("anonymous_dropdown_menu.copy_link"),
          callback: () => {
            copyToClipboard(window.location.href);
          },
        },
        {
          icon: <Icon name="language" size={IconSize.SMALL} />,
          label: t("anonymous_dropdown_menu.languages"),
          children: LANGUAGES.map((language) => ({
            label: language.label,
            callback: () => {
              i18n.changeLanguage(language.value);
            },
          })),
        },
      ]}
    >
      <Button
        icon={<Icon name="more_horiz" />}
        variant="tertiary"
        onClick={() => setIsOpen(!isOpen)}
        data-testid="anonymous-dropdown-menu"
      />
    </DropdownMenu>
  );
};
