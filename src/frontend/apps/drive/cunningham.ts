import { cunninghamConfig } from "@gouvfr-lasuite/ui-kit";

const ButtonTertiaryText = {
  "background--color-disabled": "var(--c--theme--colors--greyscale-000)",
  "color-disabled": "var(--c--theme--colors--greyscale-100)",
};

cunninghamConfig.themes.default.components.button["tertiary-text"] = {
  ...ButtonTertiaryText,
  ...cunninghamConfig.themes.default.components.button["tertiary-text"]
};

// eslint-disable-next-line import/no-anonymous-default-export
export default {
  ...cunninghamConfig, 
};


