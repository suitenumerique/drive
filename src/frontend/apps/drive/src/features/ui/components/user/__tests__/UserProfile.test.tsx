import { renderToStaticMarkup } from "react-dom/server";
import type { UserMenuProps } from "@gouvfr-lasuite/ui-components";
import { UserProfile } from "../UserProfile";

let userMenuProps: UserMenuProps | undefined;
let config: Record<string, unknown> = {};
let vault = { isEnabled: true, hasKeys: true as boolean | null };

jest.mock("@gouvfr-lasuite/ui-components", () => ({
  ...jest.requireActual("@gouvfr-lasuite/ui-components"),
  UserMenu: (props: UserMenuProps) => {
    userMenuProps = props;
    return null;
  },
}));
jest.mock("@/features/auth/Auth", () => ({
  useAuth: () => ({ user: { id: "u1", email: "user@test.fr" } }),
  logout: jest.fn(),
}));
jest.mock("@/features/config/ConfigProvider", () => ({
  useConfig: () => ({ config }),
}));
jest.mock("@/features/encryption/VaultClientProvider", () => ({
  useVaultClient: () => vault,
}));
jest.mock("@/features/layouts/components/header/Header", () => ({
  LanguagePickerUserMenu: () => null,
}));
jest.mock("@/features/encryption/ModalEncryptionOnboarding", () => ({
  ModalEncryptionOnboarding: () => null,
}));
jest.mock("@/features/encryption/ModalEncryptionSettings", () => ({
  ModalEncryptionSettings: () => null,
}));
jest.mock("@/hooks/useCopyToClipboard", () => ({
  useClipboard: () => jest.fn(),
}));
jest.mock("../../anonymous-cta/AnonymousCTA", () => ({
  AnonymousCTA: () => null,
}));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: {} }),
}));

const render = () => {
  userMenuProps = undefined;
  renderToStaticMarkup(<UserProfile />);
  return userMenuProps!;
};

describe("UserProfile settings entries", () => {
  beforeEach(() => {
    config = {};
    vault = { isEnabled: true, hasKeys: true };
  });

  it("links to the account settings and names no encryption entry when ACCOUNT_SETTINGS_URL is set", () => {
    config = { ACCOUNT_SETTINGS_URL: "https://accounts.test/" };
    const props = render();
    expect(props.settingsCTA).toBe("https://accounts.test/");
    expect(props.appSettingsCTA).toBeUndefined();
  });

  it("opens the encryption settings in Drive without ACCOUNT_SETTINGS_URL", () => {
    const props = render();
    expect(typeof props.appSettingsCTA).toBe("function");
    expect(props.settingsCTA).toBeUndefined();
  });

  it("shows no settings entry when encryption is disabled and no account settings are set", () => {
    vault = { isEnabled: false, hasKeys: null };
    const props = render();
    expect(props.appSettingsCTA).toBeUndefined();
    expect(props.settingsCTA).toBeUndefined();
  });
});
