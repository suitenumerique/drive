import Head from "next/head";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";

import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import { getItemTitle } from "@/features/explorer/utils/utils";
import { getDefaultRoute } from "@/utils/defaultRoutes";
import { formatPageTitle } from "@/features/layouts/utils/pageTitle";

export const DocumentTitle = ({ pageName }: { pageName: string }) => {
  const { t } = useTranslation();

  return (
    <Head>
      <title>{formatPageTitle(pageName, t("app_title"))}</title>
    </Head>
  );
};

/**
 * Section pages use their navigation label. A folder uses its own name,
 * so the title changes when the user opens another folder.
 */
export const ExplorerDocumentTitle = () => {
  const { t } = useTranslation();
  const router = useRouter();
  const { item } = useGlobalExplorer();
  const defaultRoute = getDefaultRoute(router.pathname);

  const pageName = defaultRoute
    ? t(defaultRoute.label)
    : item
      ? getItemTitle(item)
      : undefined;

  if (!pageName) {
    return null;
  }

  return <DocumentTitle pageName={pageName} />;
};
