import Head from "next/head";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";

import { UserReconciliation } from "@/features/auth/components/UserReconciliation";

export default function InactiveUserReconciliationPage() {
  const { t } = useTranslation();
  const {
    query: { id },
  } = useRouter();

  if (typeof id !== "string") {
    return null;
  }

  return (
    <>
      <Head>
        <meta name="robots" content="noindex" />
        <title>{`${t("user_reconciliation.title")} - Drive`}</title>
      </Head>
      <UserReconciliation userType="inactive" reconciliationId={id} />
    </>
  );
}
