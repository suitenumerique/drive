import { useRouter } from "next/router";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { WopiEditor } from "../components/WopiEditor";
import { Loader } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

export const WopiEditorPage = () => {
  const { t } = useTranslation();
  const router = useRouter();
  const itemId = router.query.id as string;

  const { data: item, isLoading } = useQuery({
    queryKey: ["item", itemId],
    queryFn: () => getDriver().getItem(itemId),
  });

  if (isLoading) {
    return <Loader aria-label={t("explorer.wopi.loading")} />;
  }

  if (!item) {
    return <div className="error">{t("explorer.wopi.error")}</div>;
  }

  return <WopiEditor item={item} />;
}; 