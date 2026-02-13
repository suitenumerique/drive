import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/features/auth/Auth";
import { getDriver } from "@/features/config/Config";
import { LANGUAGES } from "../components/header/Header";

/**
 * Auto-sync browser language to backend for new users whose
 * language field is null (e.g. just created via OIDC).
 */
export const useSyncUserLanguage = () => {
  const { user, refreshUser } = useAuth();
  const { i18n } = useTranslation();
  const driver = getDriver();

  // If user has no language, sync browser language to backend.
  // So that way wopi editors will use the correct language.
  // Frontend -> Backend.
  useEffect(() => {
    if (!user || user.language) {
      return;
    }

    const detectedLang = i18n.language?.toLowerCase();
    if (!detectedLang) {
      return;
    }

    const language = LANGUAGES.find((lang) => lang.value === detectedLang);
    if (!language) {
      return;
    }

    driver.updateUser({ language: language.value, id: user.id }).then(() => {
      void refreshUser?.();
    });
  }, [user, i18n.language, driver, refreshUser]);

  // On first load, if user has a language, sync it to the browser.
  // Deps is set on user?.id to prevent a new call when refreshing user.
  // We only want to call this effect one time after user is fetched.
  // Backend -> Frontend.
  useEffect(() => {
    if (!user) {
      return;
    }
    if (!user.language) {
      return;
    }
    i18n.changeLanguage(user.language).catch((err) => {
      console.error("Error changing language", err);
    });
  }, [user?.id]);
};
