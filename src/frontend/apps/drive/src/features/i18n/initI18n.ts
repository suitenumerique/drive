import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import { LANGUAGES_ALLOWED, LANGUAGE_LOCAL_STORAGE } from "./conf";
import resources from "./translations.json";

/**
 * How language works:
 *
 * - First visit on the website, the user is not logged in, we detect the browser current language with LanguageDetector
 * - When the user logs in, its language attribute is null
 * - Because the user language is null, we use the language detected by LanguageDetector
 * - If the user changes the language via the language picker, we update the language of the user via a request to the backend
 * - Now, the language used is the language of the user ( when user is fetched, LanguagePicker calls LanguagePicker via useEffect )
 *
 * This way we ensure that we use the most probable language of the user.
 */

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    detection: {
      order: ["cookie", "navigator"],
      caches: ["cookie"],
      lookupCookie: "drive_language",
      cookieMinutes: 525600,
      cookieOptions: {
        path: "/",
        sameSite: "lax",
      },
    },
    interpolation: {
      escapeValue: false,
    },
    preload: LANGUAGES_ALLOWED,
  })
  .catch(() => {
    throw new Error("i18n initialization failed");
  });

// Save language in local storage
i18n.on("languageChanged", (lng) => {
  if (typeof window !== "undefined") {
    localStorage.setItem(LANGUAGE_LOCAL_STORAGE, lng);
  }
});

export default i18n;
