import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { useApiConfig } from "./useApiConfig";
import { ApiConfig } from "@/features/drivers/types";
import { createContext, useContext, useEffect } from "react";
import { useAppContext } from "@/pages/_app";

export interface ConfigContextType {
  config: ApiConfig;
}

export const ConfigContext = createContext<ConfigContextType | undefined>(
  undefined
);

export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error("useConfig must be used within a ConfigProvider");
  }
  return context;
};

export const ConfigProvider = ({ children }: { children: React.ReactNode }) => {
  const { data: config } = useApiConfig();
  const { setTheme } = useAppContext();

  useEffect(() => {
    if (config?.FRONTEND_THEME) {
      setTheme(config.FRONTEND_THEME);
    }
  }, [config?.FRONTEND_THEME, setTheme]);

  if (!config) {
    return (
      <div className="global-loader">
        <Spinner size="xl" />
      </div>
    );
  }

  return (
    <ConfigContext.Provider value={{ config }}>
      {children}
    </ConfigContext.Provider>
  );
};
