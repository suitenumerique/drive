import {
  DropdownMenu,
  Icon,
  IconSize,
  useDropdownMenu,
  UserMenu,
} from "@gouvfr-lasuite/ui-kit";
import { useAuth } from "@/features/auth/Auth";
import { logout } from "@/features/auth/Auth";
import {
  LanguagePickerUserMenu,
  LANGUAGES,
} from "@/features/layouts/components/header/Header";
import { AnonymousCTA } from "../anonymous-cta/AnonymousCTA";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { useClipboard } from "@/hooks/useCopyToClipboard";

export const UserProfile = () => {
  const { user } = useAuth();
  return (
    <>
      {user ? (
        <UserMenu
          user={user}
          logout={logout}
          termOfServiceUrl="https://docs.numerique.gouv.fr/docs/8e298e03-c95f-44c7-be4a-ffb618af1854/"
          actions={<LanguagePickerUserMenu />}
        />
      ) : (
        <>
          <AnonymousDropdownMenu />
          <AnonymousCTA />
        </>
      )}
    </>
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
