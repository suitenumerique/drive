import type { LaGaufreV2Props } from "@gouvfr-lasuite/ui-components";

type GaufreDefaults = {
  widgetPath: string;
  apiUrl: string;
  showMoreLimit: number;
};

/**
 * Pick the waffle props: the `waffle` entry of the theme customization file
 * when it provides a list of services (`apiUrl` or `data`), otherwise the
 * defaults of the Cunningham theme.
 */
export const resolveGaufreProps = (
  custom: LaGaufreV2Props | undefined,
  defaults: GaufreDefaults,
): LaGaufreV2Props => {
  if (!custom?.apiUrl && !custom?.data) {
    return defaults;
  }

  return {
    widgetPath: defaults.widgetPath,
    showMoreLimit: defaults.showMoreLimit,
    ...custom,
  };
};
