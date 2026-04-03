import { cunninghamConfig } from "@gouvfr-lasuite/ui-kit";
import deepMerge from "deepmerge";

const themesImages = {
  "anct-light": {
    favicon: "/assets/anct_favicon.png",
    logo: "/assets/anct_logo_beta.svg",
    "logo-icon": "/assets/anct_logo-icon.svg",
  },
  "dsfr-dark": {
    favicon: "/assets/favicon.png",
    logo: "/assets/logo_beta.svg",
    "logo-icon": "/assets/logo-icon_beta.svg",
  },
  "dsfr-light": {
    favicon: "/assets/favicon.png",
    logo: "/assets/logo_beta.svg",
    "logo-icon": "/assets/logo-icon_beta.svg",
  },
};

const themesGaufre = {
  "anct-light": {
    widgetPath: "https://static.suite.anct.gouv.fr/widgets/lagaufre.js",
    apiUrl:
      "https://operateurs.suite.anct.gouv.fr/api/v1.0/lagaufre/services/?operator=9f5624fc-ef99-4d10-ae3f-403a81eb16ef&siret=21870030000013",
  },
  "dsfr-dark": {
    widgetPath: "https://static.suite.anct.gouv.fr/widgets/lagaufre.js",
    apiUrl: "https://lasuite.numerique.gouv.fr/api/services",
  },
  "dsfr-light": {
    widgetPath: "https://static.suite.anct.gouv.fr/widgets/lagaufre.js",
    apiUrl: "https://lasuite.numerique.gouv.fr/api/services",
  },
};

const getComponents = (theme: keyof typeof themesImages) => {
  return {
    datagrid: {
      "body--background-color-hover":
        "ref(contextuals.background.semantic.contextual.primary)",
    },
    gaufre: {
      widgetPath: `'${themesGaufre[theme].widgetPath}'`,
      apiUrl: `'${themesGaufre[theme].apiUrl}'`,
    },
    favicon: {
      src: `'${themesImages[theme].favicon}'`,
    },
    logo: {
      src: `url('${themesImages[theme].logo}')`,
    },
    "logo-icon": {
      src: `url('${themesImages[theme]["logo-icon"]}')`,
    },
  };
};

const defaultConfig = deepMerge(cunninghamConfig, {
  themes: {
    "anct-light": {
      components: getComponents("anct-light"),
    },
    "dsfr-light": {
      components: getComponents("dsfr-light"),
    },
    "dsfr-dark": {
      components: getComponents("dsfr-dark"),
    },
  },
});

const config = defaultConfig;

export default config;
