import type { ReactElement, ReactNode } from "react";
import type { NextPage } from "next";
import type { AppProps } from "next/app";
import { CunninghamProvider } from "@openfun/cunningham-react";

import "../styles/globals.scss";
import "./../i18n/initI18n";

export type NextPageWithLayout<P = {}, IP = P> = NextPage<P, IP> & {
  getLayout?: (page: ReactElement) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};

export default function MyApp({ Component, pageProps }: AppPropsWithLayout) {
  // Use the layout defined at the page level, if available
  const getLayout = Component.getLayout ?? ((page) => page);

  return (
    <CunninghamProvider theme="dsfr">
      {getLayout(<Component {...pageProps} />)}
    </CunninghamProvider>
  );
}
