import { userMenuSettingsCTAs } from "../encryptionSettingsMenu";

describe("userMenuSettingsCTAs", () => {
  const openEncryptionSettings = jest.fn();

  it.each([true, false])(
    "links to the account settings, and nothing else, when the deployment names them (encryption %p)",
    (isEncryptionEnabled) => {
      expect(
        userMenuSettingsCTAs({
          isEncryptionEnabled,
          accountSettingsUrl: "https://accounts.test/",
          openEncryptionSettings,
        }),
      ).toEqual({ settingsCTA: "https://accounts.test/" });
    },
  );

  it.each([null, undefined, ""])(
    "opens the encryption settings in Drive without account settings (%p)",
    (accountSettingsUrl) => {
      expect(
        userMenuSettingsCTAs({
          isEncryptionEnabled: true,
          accountSettingsUrl,
          openEncryptionSettings,
        }),
      ).toEqual({ appSettingsCTA: openEncryptionSettings });
    },
  );

  it("shows no settings entry without account settings or encryption", () => {
    expect(
      userMenuSettingsCTAs({
        isEncryptionEnabled: false,
        accountSettingsUrl: null,
        openEncryptionSettings,
      }),
    ).toEqual({});
  });
});
