export type AppLanguage = {
  /**
   * Django's casing, and the single canonical language value across the app:
   * i18next resource key, "drive_language" cookie and user.language.
   */
  value: string;
  label: string;
  shortLabel: string;
};

/**
 * Authoritative list of the languages we ship. It must stay in sync with the
 * keys of translations.json, and is ordered by display priority in the
 * language picker.
 */
export const LANGUAGES: AppLanguage[] = [
  {
    label: "Français",
    value: "fr-fr",
    shortLabel: "FR",
  },
  {
    label: "English",
    value: "en-us",
    shortLabel: "EN",
  },
  {
    label: "Nederlands",
    value: "nl-nl",
    shortLabel: "NL",
  },
];

export const LANGUAGES_ALLOWED = LANGUAGES.map(({ value }) => value);

export const DEFAULT_LANGUAGE = "en-us";

export const LANGUAGE_LOCAL_STORAGE = "main-language";
