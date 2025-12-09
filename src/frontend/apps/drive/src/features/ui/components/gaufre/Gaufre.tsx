import { LaGaufreV2 } from "@gouvfr-lasuite/ui-kit";
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
  const widgetPath = removeQuotes(theme.components.gaufre.widgetPath);
  const apiUrl = removeQuotes(theme.components.gaufre.apiUrl);

  if (hideGaufre) {
    return null;
  }

  return (
    <LaGaufreV2
      widgetPath={widgetPath}
      apiUrl={apiUrl}
      showMoreLimit={themeName === "anct" ? 100 : 6}
    />
  );
};
