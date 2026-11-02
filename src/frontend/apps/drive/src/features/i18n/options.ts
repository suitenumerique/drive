import type { InitOptions } from "i18next";

import { DEFAULT_LANGUAGE, LANGUAGES_ALLOWED } from "./conf";
import resources from "./translations.json";

/**
 * Kept apart from initI18n so the resolution rules can be asserted without
 * booting the shared instance, and so the tests exercise the very options we
 * ship rather than a copy of them.
 */
export const i18nOptions: InitOptions = {
  resources,
  fallbackLng: DEFAULT_LANGUAGE,
  // Browsers are free to announce a language without a region: Firefox in
  // French sends "fr" where Chrome sends "fr-FR". Declaring what we ship lets
  // i18next widen a bare code to the variant we have, instead of falling all
  // the way back to English ( it was the case before when Firefox was giving
  // "fr" instead of "fr-FR", it was causing issues with the translations inside
  // CunninghamProvider )
  supportedLngs: LANGUAGES_ALLOWED,
  // Our resource keys follow Django's casing ("fr-fr"), not the canonical
  // BCP 47 one ("fr-FR") that i18next would otherwise produce.
  lowerCaseLng: true,
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
};
