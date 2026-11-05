/** Neutral gray theme, the same default Docs, Meet and Conversations use. */
export const DEFAULT_FRONTEND_THEME = "default";

export const resolveFrontendTheme = (theme?: string | null) => {
  if (!theme) {
    return DEFAULT_FRONTEND_THEME;
  }

  return theme;
};
