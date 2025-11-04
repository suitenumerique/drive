import { DropdownMenu, LaGaufre } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import { useAuth, logout } from "@/features/auth/Auth";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/app-view/ExplorerSearchButton";
import { getDriver } from "@/features/config/Config";
import { useConfig } from "@/features/config/ConfigProvider";
import { Feedback } from "@/features/feedback/Feedback";
import { LoginButton } from "@/features/auth/components/LoginButton";
import { Item } from "@/features/drivers/types";
import { ItemFilters } from "@/features/drivers/Driver";
import { useIsMinimalLayout } from "@/utils/useLayout";

export const HeaderIcon = () => {
  return (
    <div className="drive__header__left">
      <div className="drive__header__logo" />
      <Feedback />
    </div>
  );
};

export const HeaderRight = ({
  displaySearch,
  currentItem,
}: {
  displaySearch?: boolean;
  currentItem?: Item;
}) => {
  const { user } = useAuth();
  const isMinimalLayout = useIsMinimalLayout();

  const defaultFilters: ItemFilters = useMemo(() => {
    const workspaceId = currentItem?.parents?.[0]?.id ?? currentItem?.id;

    if (isMinimalLayout) {
      return {
        workspace: workspaceId,
      };
    }
    return {};
  }, [currentItem, isMinimalLayout]);

  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  const { config } = useConfig();
  return (
    <>
      {user && displaySearch && (
        <ExplorerSearchButton defaultFilters={defaultFilters} />
      )}
      {user ? (
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
            variant="tertiary"
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
      ) : (
        <LoginButton />
      )}
      <LanguagePicker />
      {!config?.FRONTEND_HIDE_GAUFRE && <LaGaufre />}
    </>
  );
};

export const LanguagePicker = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const driver = getDriver();
  // We must set the language to lowercase because django does not use "en-US", but "en-us".
  const [selectedValues, setSelectedValues] = useState([
    user?.language || i18n.language.toLowerCase(),
  ]);
  const languages = [
    { label: "Français", value: "fr-fr" },
    { label: "English", value: "en-us" },
    { label: "Nederlands", value: "nl-nl" },
  ];

  // Make sure the language of the ui is in the same language as the user.
  useEffect(() => {
    if (user?.language) {
      i18n.changeLanguage(user.language).catch((err) => {
        console.error("Error changing language", err);
      });
    }
  }, [user?.language]);

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
        variant="tertiary"
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
