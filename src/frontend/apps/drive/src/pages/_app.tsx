import {
  createContext,
  useContext,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";
import type { NextPage } from "next";
import type { AppProps } from "next/app";
import { CunninghamProvider } from "@gouvfr-lasuite/ui-kit";
import {
  MutationCache,
  Query,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

import "../styles/globals.scss";
import "../features/i18n/initI18n";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { APIError, errorToString } from "@/features/api/APIError";
import Head from "next/head";
import { useTranslation } from "react-i18next";
import { AnalyticsProvider } from "@/features/analytics/AnalyticsProvider";
import { capitalizeRegion } from "@/features/i18n/utils";
import { FeedbackFooterMobile } from "@/features/feedback/Feedback";
import { ConfigProvider } from "@/features/config/ConfigProvider";
import {
  removeQuotes,
  useCunninghamTheme,
} from "@/features/ui/cunningham/useCunninghamTheme";
import { ResponsiveDivs } from "@/features/ui/components/responsive/ResponsiveDivs";
import { useRouter } from "next/router";
import { useMemo } from "react";

export type NextPageWithLayout<P = object, IP = P> = NextPage<P, IP> & {
  getLayout?: (page: ReactElement) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};
const onError = (error: Error, query: unknown) => {
  if ((query as Query).meta?.noGlobalError) {
    return;
  }

  // Don't show toast for 401/403 errors because the app handles them by
  // redirecting to the 401/403 page. So we don't want to show a toast before
  // the redirect, it would feels buggy.
  if (error instanceof APIError && (error.code === 401 || error.code === 403)) {
    return;
  }

  addToast(
    <ToasterItem type="error">
      <span>{errorToString(error)}</span>
    </ToasterItem>
  );
};

const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (error, variables, context, mutation) => {
      onError(error, mutation);
    },
  }),
  queryCache: new QueryCache({
    onError: (error, query) => onError(error, query),
  }),
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

export interface AppContextType {
  theme: string;
  setTheme: (theme: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within an AppContextProvider");
  }
  return context;
};

export default function MyApp({
  Component,
  pageProps,
  router,
}: AppPropsWithLayout) {
  const [theme, setTheme] = useState<string>("default");

  return (
    <AppContext.Provider value={{ theme, setTheme }}>
      <MyAppInner Component={Component} pageProps={pageProps} router={router} />
    </AppContext.Provider>
  );
}

const MyAppInner = ({ Component, pageProps }: AppPropsWithLayout) => {
  // Use the layout defined at the page level, if available
  const getLayout = Component.getLayout ?? ((page) => page);
  const { t, i18n } = useTranslation();
  const { theme } = useAppContext();
  const themeTokens = useCunninghamTheme();

  const router = useRouter();
  const isSdk = useMemo(
    () => router.pathname.startsWith("/sdk"),
    [router.pathname]
  );
  return (
    <>
      <Head>
        <title>{t("app_title")}</title>
        <link
          rel="icon"
          href={removeQuotes(themeTokens.components.favicon.src)}
          type="image/png"
        />
      </Head>
      <QueryClientProvider client={queryClient}>
        <CunninghamProvider
          currentLocale={capitalizeRegion(i18n.language)}
          theme={theme}
        >
          <ConfigProvider>
            <AnalyticsProvider>
              {getLayout(<Component {...pageProps} />)}
              <ResponsiveDivs />
              {!isSdk && <FeedbackFooterMobile />}
            </AnalyticsProvider>
          </ConfigProvider>
        </CunninghamProvider>
      </QueryClientProvider>
    </>
  );
};
