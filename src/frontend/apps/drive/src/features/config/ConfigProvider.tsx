import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { useApiConfig } from "./useApiConfig";
import { ApiConfig } from "@/features/drivers/types";
import { createContext, useContext, useEffect } from "react";
import { useAppContext } from "@/pages/_app";
import { setRuntimeConfig } from "./runtimeConfig";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { getOperationTimeBound } from "@/features/operations/timeBounds";
import { useTimeBoundedPhase } from "@/features/operations/useTimeBoundedPhase";

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
  const { t } = useTranslation();
  const { data: config, isLoading, isError, refetch } = useApiConfig();
  const { setTheme } = useAppContext();

  useEffect(() => {
    if (config?.FRONTEND_THEME) {
      setTheme(config.FRONTEND_THEME);
    } else {
      setTheme("default");
    }
  }, [config?.FRONTEND_THEME, setTheme]);

  useEffect(() => {
    if (config) {
      setRuntimeConfig(config);
    }
  }, [config]);

  const bounds = getOperationTimeBound("config_load");
  const phase = useTimeBoundedPhase(isLoading, bounds);

  if (isError) {
    return (
      <div className="global-loader">
        <div>{t("operations.long_running.failed")}</div>
        <Button variant="tertiary" onClick={() => refetch()}>
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="global-loader">
        <Spinner size="xl" />
        {phase !== "loading" && (
          <div>
            {phase === "still_working"
              ? t("operations.long_running.still_working")
              : t("operations.long_running.failed")}
          </div>
        )}
        {phase === "failed" && (
          <Button variant="tertiary" onClick={() => refetch()}>
            {t("common.retry")}
          </Button>
        )}
      </div>
    );
  }

  return (
    <ConfigContext.Provider value={{ config }}>
      {children}
    </ConfigContext.Provider>
  );
};
