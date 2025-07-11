import { useAppContext } from "@/pages/_app";
import { tokens } from "@/styles/cunningham-tokens";

export const useCunninghamTheme = () => {
  const { theme } = useAppContext();

  return tokens.themes[
    theme as keyof typeof tokens.themes
  ] as (typeof tokens.themes)["default"];
};

// Once the cunningham sass generated string is fixed, we can remove this function.
export const removeQuotes = (str: string) => {
  return str.replace(/^['"]|['"]$/g, "");
};
