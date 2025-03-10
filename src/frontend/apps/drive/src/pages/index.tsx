import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import Head from "next/head";
import { useTranslation } from "next-i18next";
import { DefaultLayout } from "@/features/layouts/components/default/DefaultLayout";
import { ProConnectButton } from "@lasuite/ui-kit";
import { login, useAuth } from "@/features/auth/Auth";
import { gotoLastVisitedItem } from "@/features/explorer/utils/utils";
import { useEffect } from "react";
export default function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      gotoLastVisitedItem();
    }
  }, [user]);

  if (user) {
    return null;
  }

  return (
    <>
      <Head>
        <title>{t("app_title")}</title>
        <meta name="description" content={t("app_description")} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.png" />
      </Head>
      <div>
        {t("welcome")}
        <ProConnectButton onClick={login} />
      </div>
    </>
  );
}

HomePage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <DefaultLayout>{page}</DefaultLayout>
    </GlobalLayout>
  );
};
