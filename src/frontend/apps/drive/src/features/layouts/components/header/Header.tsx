import { DropdownMenu, Header as KitHeader } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import logo from "@/assets/logo.svg";
import { useAuth, logout } from "@/features/auth/Auth";
import { useState } from "react";
import { useTranslation } from "react-i18next";

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
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  return (
    <div className="c__header-right">
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
    </div>
  );
};

const LanguagePicker = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { i18n } = useTranslation();
  const [selectedValues, setSelectedValues] = useState([i18n.language]);
  const languages = [
    { label: "FR", value: "fr" },
    { label: "EN", value: "en" },
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
