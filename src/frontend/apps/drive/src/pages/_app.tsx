import type { ReactElement, ReactNode } from "react";
import type { NextPage } from "next";
import type { AppProps } from "next/app";
import { CunninghamProvider } from "@lasuite/ui-kit";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../styles/globals.scss";
import "../features/i18n/initI18n";

export type NextPageWithLayout<P = {}, IP = P> = NextPage<P, IP> & {
  getLayout?: (page: ReactElement) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};

const queryClient = new QueryClient();

export default function MyApp({ Component, pageProps }: AppPropsWithLayout) {
  // Use the layout defined at the page level, if available
  const getLayout = Component.getLayout ?? ((page) => page);

  return (
    <QueryClientProvider client={queryClient}>
      <CunninghamProvider>
        {getLayout(<Component {...pageProps} />)}
      </CunninghamProvider>
    </QueryClientProvider>
  );
}
