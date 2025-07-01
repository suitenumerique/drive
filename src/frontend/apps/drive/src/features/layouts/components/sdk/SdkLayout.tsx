import { Auth } from "@/features/auth/Auth";
import {
  ExplorerContext,
  ExplorerProvider,
} from "@/features/explorer/components/ExplorerContext";
import { ExplorerDndProvider } from "@/features/explorer/components/ExplorerDndProvider";
import { PickerFooter } from "@/features/sdk/SdkPickerFooter";
import { createContext, useContext, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export const getSdkLayout = (page: React.ReactElement) => {
  return <SdkLayout>{page}</SdkLayout>;
};

/**
 * Picker.
 */

export const getSdkPickerLayout = (page: React.ReactElement) => {
  return <SdkPickerLayout>{page}</SdkPickerLayout>;
};

export const SdkContext = createContext<{
  token: string;
}>({
  token: "",
});

export const useSdkContext = () => {
  const context = useContext(SdkContext);
  if (!context) {
    throw new Error("useSdkContext must be used within a SdkContext");
  }
  return context;
};

export const SdkPickerLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(sessionStorage.getItem("sdk_token"));
  }, [token]);

  if (!token) {
    return null;
  }

  return (
    <SdkContext.Provider value={{ token }}>
      <SdkLayout>{children}</SdkLayout>
    </SdkContext.Provider>
  );
};

/**
 * SDK.
 */

export const SdkLayout = ({ children }: { children: React.ReactNode }) => {
  const { t } = useTranslation();

  return (
    <Auth>
      <ExplorerProvider displayMode="sdk" itemId="" onNavigate={() => {}}>
        <div className="explorer__sdk__header">
          {t("sdk.explorer.picker_caption")}
        </div>
        {children}
      </ExplorerProvider>
    </Auth>
  );
};
