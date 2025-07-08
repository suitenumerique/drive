import { cunninghamConfig } from "@gouvfr-lasuite/ui-kit";


// TODO: Temporary solution to override the default button tertiary text color, waiting for the new ui-kit to be released
const ButtonTertiaryText = {
  "background--color-disabled": "var(--c--theme--colors--greyscale-000)",
  "color-disabled": "var(--c--theme--colors--greyscale-100)",
};

cunninghamConfig.themes.default.components.button["tertiary-text"] = {
  ...ButtonTertiaryText,
  ...cunninghamConfig.themes.default.components.button["tertiary-text"]
};

 
const config = {
  ...cunninghamConfig, 
  themes: {
    ...cunninghamConfig.themes,
    default: {
      ...cunninghamConfig.themes.default,
      components: {
        ...cunninghamConfig.themes.default.components,
        favicon: {
          src: "'/assets/favicon.png'",
        },
        logo: {
          src: "url('/assets/logo_alpha.svg')",
        },
        "logo-icon": {
          src: "url('/assets/logo-icon_alpha.svg')",
        },
      },
    },
    anct: {
      components: {
        favicon: {
          src: "'/assets/anct_favicon.png'",
        },
        logo: {
          src: "url('/assets/anct_logo_alpha.svg')",
        },
        "logo-icon": {
          src: "url('/assets/anct_logo-icon.svg')",
        },
      },
    },
  },
};

export default config;


