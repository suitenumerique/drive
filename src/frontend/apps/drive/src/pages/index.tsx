import { GlobalLayout } from "@/components/layouts/global/GlobalLayout";
import Head from "next/head";
import Link from "next/link";
import { useTranslation } from "next-i18next";

export default function HomePage() {
  const { t } = useTranslation();
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
        <Link href="/explorer/items/truc">Go to fichiers</Link>
      </div>
    </>
  );
}

HomePage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};
