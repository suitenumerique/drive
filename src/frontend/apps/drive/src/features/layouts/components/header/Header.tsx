import {
  DropdownMenu,
  Header as KitHeader,
  LaGaufre,
} from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import { useRouter } from 'next/navigation';
import logo from "@/assets/logo.svg";
import { useAuth, logout } from "@/features/auth/Auth";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/ExplorerSearchButton";
import { getDriver } from "@/features/config/Config";

export const Header = () => {
  return (
    <KitHeader
      leftIcon={<img src={logo.src} alt="logo" />}
      rightIcon={<HeaderRight />}
    />
  );
};

export const HeaderRight = () => {
  const { user } = useAuth();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  return (
    <>
      {user && (
        <DropdownMenu
          options={[
            {
              label: t("logout"),
              icon: <span className="material-icons">logout</span>,
              callback: logout,
            },
          ]}
          isOpen={isOpen}
          onOpenChange={setIsOpen}
        >
          <Button
            onClick={() => router.push(`/user-tokens`)}
            aria-label={t('API Tokens', 'API Tokens')}
            color="primary-text"
          >
            {t('API Tokens', 'API Tokens')}
          </Button>
          <Button
            color="primary-text"
            onClick={() => setIsOpen(!isOpen)}
            icon={
              <span className="material-icons">
                {isOpen ? "arrow_drop_up" : "arrow_drop_down"}
              </span>
            }
            iconPosition="right"
          >
            {t("my_account")}
          </Button>
        </DropdownMenu>
      )}
      <LanguagePicker />
      <LaGaufre />
      <ExplorerSearchButton />
    </>
  );
};

export const LanguagePicker = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const driver = getDriver();
  const [selectedValues, setSelectedValues] = useState([
    user?.language || i18n.language,
  ]);
  const languages = [
    { label: "Français", value: "fr-fr" },
    { label: "English", value: "en-us" },
  ];

  return (
    <DropdownMenu
      options={languages}
      isOpen={isOpen}
      onOpenChange={setIsOpen}
      onSelectValue={(value) => {
        setSelectedValues([value]);
        i18n.changeLanguage(value).catch((err) => {
          console.error("Error changing language", err);
        });
        if (user) {
          driver.updateUser({ language: value, id: user.id });
        }
      }}
      selectedValues={selectedValues}
    >
      <Button
        onClick={() => setIsOpen(!isOpen)}
        color="primary-text"
        className="c__language-picker"
        icon={
          <span className="material-icons">
            {isOpen ? "arrow_drop_up" : "arrow_drop_down"}
          </span>
        }
        iconPosition="right"
      >
        <span className="material-icons">translate</span>
        <span className="c__language-picker__label">
          {languages.find((lang) => lang.value === selectedValues[0])?.label}
        </span>
      </Button>
    </DropdownMenu>
  );
};
