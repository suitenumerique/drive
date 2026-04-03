import { Spinner } from "@gouvfr-lasuite/ui-kit";
import Head from "next/head";
import Script from "next/script";
import { useApiConfig } from "./useApiConfig";
import { ApiConfig } from "@/features/drivers/types";
import { createContext, useContext, useEffect } from "react";
import { useAppContext } from "@/pages/_app";

export interface ConfigContextType {
  config: ApiConfig;
}

export const ConfigContext = createContext<ConfigContextType | undefined>(
  undefined,
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
    } else {
      setTheme("dsfr-light");
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
      {config.FRONTEND_CSS_URL && (
        <Head>
          <link rel="stylesheet" href={config.FRONTEND_CSS_URL} />
        </Head>
      )}
      {config.FRONTEND_JS_URL && <Script src={config.FRONTEND_JS_URL} />}
      {children}
    </ConfigContext.Provider>
  );
};
