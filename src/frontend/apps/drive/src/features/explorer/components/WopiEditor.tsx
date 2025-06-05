import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { getOrigin } from "@/features/api/utils";

interface WopiEditorProps {
  item: Item;
}

export const WopiEditor = ({ item }: WopiEditorProps) => {
  const { t } = useTranslation();
  const formRef = useRef<HTMLFormElement>(null);

  const { data: wopiInfo, isLoading, isError } = useQuery({
    queryKey: ["item", item.id, "wopi"],
    queryFn: () => getDriver().getWopiInfo(item.id),
  });

  useEffect(() => {
    if (wopiInfo && formRef.current) {
      formRef.current.submit();
    }
  }, [wopiInfo]);

  if (isLoading) {
    return <div>{t("explorer.wopi.loading")}</div>;
  }

  if (isError || !wopiInfo) {
    return <div className="error">{t("explorer.wopi.error")}</div>;
  }


  return (
    <div className="wopi-editor">
      <form
        ref={formRef}
        name="office_form"
        target="office_frame"
        action={wopiInfo.launch_url}
        method="post"
      >
        <input name="access_token" value={wopiInfo.access_token} type="hidden" />
        <input name="access_token_ttl" value={wopiInfo.access_token_ttl} type="hidden" />
      </form>
      <iframe
        name="office_frame"
        title={item.title}
        style={{ width: "100%", height: "100vh", border: "none" }}
      />
    </div>
  );
}; 