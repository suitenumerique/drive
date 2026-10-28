/**
 * The user menu's settings entries. With the suite's account settings
 * (ACCOUNT_SETTINGS_URL), "Manage account" links there, where encryption is
 * managed too, so the generic menu names nothing about encryption. Without
 * them, the application settings entry opens the encryption settings in Drive
 * when the feature is on.
 */
export const userMenuSettingsCTAs = ({
  isEncryptionEnabled,
  accountSettingsUrl,
  openEncryptionSettings,
}: {
  isEncryptionEnabled: boolean;
  accountSettingsUrl: string | null | undefined;
  openEncryptionSettings: () => void;
}): {
  settingsCTA?: string;
  appSettingsCTA?: () => void;
} => {
  if (accountSettingsUrl) {
    return { settingsCTA: accountSettingsUrl };
  }
  return isEncryptionEnabled ? { appSettingsCTA: openEncryptionSettings } : {};
};
