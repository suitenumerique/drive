import { renderToStaticMarkup } from "react-dom/server";
import type { UserMenuProps } from "@gouvfr-lasuite/ui-components";
import { UserProfile } from "../UserProfile";

let userMenuProps: UserMenuProps | undefined;
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
    vault = { isEnabled: true, hasKeys: true };
  });

  it("opens the encryption settings in Drive when encryption is enabled", () => {
    const props = render();
    expect(typeof props.appSettingsCTA).toBe("function");
    expect(props.settingsCTA).toBeUndefined();
  });

  it("shows no settings entry when encryption is disabled", () => {
    vault = { isEnabled: false, hasKeys: null };
    const props = render();
    expect(props.appSettingsCTA).toBeUndefined();
    expect(props.settingsCTA).toBeUndefined();
  });
});
