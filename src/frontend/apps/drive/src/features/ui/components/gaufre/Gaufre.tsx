import { LaGaufreV2 } from "@gouvfr-lasuite/ui-components";
import {
  removeQuotes,
  useCunninghamTheme,
} from "../../cunningham/useCunninghamTheme";
import { useConfig } from "@/features/config/ConfigProvider";
import { useAppContext } from "@/pages/_app";

export const Gaufre = () => {
  const { config } = useConfig();
  const { theme: themeName } = useAppContext();
  const hideGaufre = config?.FRONTEND_HIDE_GAUFRE;
  const theme = useCunninghamTheme();
  // Only the dsfr-*/anct-light themes carry gaufre tokens. On the neutral
  // themes there are none, which used to throw here — and leaves the widget
  // off, which is the right default: it loads a third-party script and lists
  // one operator's services.
  const gaufre = theme.components.gaufre as
    | { widgetPath: string; apiUrl: string }
    | undefined;
  const widgetPath = gaufre && removeQuotes(gaufre.widgetPath);
  const apiUrl = gaufre && removeQuotes(gaufre.apiUrl);

  if (hideGaufre || !widgetPath || !apiUrl) {
    return null;
  }

  return (
    <LaGaufreV2
      widgetPath={widgetPath}
      apiUrl={apiUrl}
      showMoreLimit={themeName.includes("anct") ? 100 : 6}
    />
  );
};
