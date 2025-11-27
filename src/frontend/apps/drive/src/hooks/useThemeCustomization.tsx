import { useConfig } from "@/features/config/ConfigProvider";
import { ThemeCustomization } from "@/features/drivers/types";
import { splitLocaleCode } from "@/features/i18n/utils";
import { useTranslation } from "react-i18next";

export const useThemeCustomizationFooter = () => {
  const { config } = useConfig();
  const { i18n } = useTranslation();
  const language = splitLocaleCode(i18n.language).language;
  const themeCustomization = config?.theme_customization?.footer;
  return {
    ...themeCustomization?.default,
    ...(themeCustomization?.[language as keyof typeof themeCustomization] ??
      {}),
  };
};

export const useThemeCustomizationElementsDisplay = (key: keyof Pick<ThemeCustomization, 'auth_buttons' | 'language_picker'>) => {
  const { config } = useConfig();
  const themeCustomization = config?.theme_customization?.[key];

  return {
    ...(themeCustomization ?? {})
  }
}
