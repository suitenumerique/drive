import { LanguagePicker, useResponsive } from "@gouvfr-lasuite/ui-kit";
import { useAuth } from "@/features/auth/Auth";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ExplorerSearchButton } from "@/features/explorer/components/app-view/ExplorerSearchButton";
import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { ItemFilters } from "@/features/drivers/Driver";
import { useIsMinimalLayout } from "@/utils/useLayout";
import { Feedback } from "@/features/feedback/Feedback";
import { Gaufre } from "@/features/ui/components/gaufre/Gaufre";
import { UserProfile } from "@/features/ui/components/user/UserProfile";

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

  const { isTablet } = useResponsive();

  const defaultFilters: ItemFilters = useMemo(() => {
    const workspaceId = currentItem?.parents?.[0]?.id ?? currentItem?.id;

    if (isMinimalLayout) {
      return {
        workspace: workspaceId,
      };
    }
    return {};
  }, [currentItem, isMinimalLayout]);

  return (
    <>
      {user && displaySearch && (
        <ExplorerSearchButton defaultFilters={defaultFilters} />
      )}

      {!isTablet && (
        <>
          <Gaufre />
          <UserProfile />
        </>
      )}
    </>
  );
};

export const LanguagePickerUserMenu = () => {
  const { i18n } = useTranslation();
  const { user, refreshUser } = useAuth();
  const driver = getDriver();
  const [selectedLanguage, setSelectedLanguage] = useState(user?.language);

  // We must set the language to lowercase because django does not use "en-US", but "en-us".

  const languages = [
    {
      label: "Français",
      value: "fr-fr",
      shortLabel: "FR",
      isChecked: selectedLanguage === "fr-fr",
    },
    {
      label: "English",
      value: "en-us",
      shortLabel: "EN",
      isChecked: selectedLanguage === "en-us",
    },
    {
      label: "Nederlands",
      value: "nl-nl",
      shortLabel: "NL",
      isChecked: selectedLanguage === "nl-nl",
    },
    {
      label: "Deutsch",
      value: "de-de",
      shortLabel: "DE",
      isChecked: selectedLanguage === "de-de",
    },
  ];

  const onChange = (value: string) => {
    setSelectedLanguage(value);
    i18n.changeLanguage(value).catch((err) => {
      console.error("Error changing language", err);
    });
    if (user) {
      driver.updateUser({ language: value, id: user.id }).then(() => {
        void refreshUser?.();
      });
    }
  };

  return (
    <LanguagePicker
      languages={languages}
      size="small"
      onChange={onChange}
      compact
    />
  );
};
