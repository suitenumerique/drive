import { LanguagePicker, useResponsive } from "@gouvfr-lasuite/ui-components";
import { useAuth } from "@/features/auth/Auth";
import { LANGUAGES } from "@/features/i18n/conf";
import { useMemo } from "react";
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
  // i18n.language is always one of LANGUAGES_ALLOWED and already reflects the
  // user, then the cookie, then the browser: it is the active language.
  const languages = useMemo(() => {
    return LANGUAGES.map((language) => ({
      ...language,
      isChecked: language.value === i18n.language,
    }));
  }, [i18n.language]);

  const onChange = (value: string) => {
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
