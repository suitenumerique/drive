import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { FilePreviewType } from "../files-preview/FilesPreview";
import { ErrorPreview } from "../error/ErrorPreview";

interface WopiEditorProps {
  item: FilePreviewType;
}

export const WopiEditor = ({ item }: WopiEditorProps) => {
  const { t } = useTranslation();
  const formRef = useRef<HTMLFormElement>(null);

  const {
    data: wopiInfo,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["item", item.id, "wopi"],
    refetchOnWindowFocus: false,
    queryFn: () => getDriver().getWopiInfo(item.id),
  });

  useEffect(() => {
    if (wopiInfo && formRef.current) {
      formRef.current.submit();
    }
  }, [wopiInfo]);

  if (isLoading) {
    return <div>{t("file_preview.wopi.loading")}</div>;
  }

  if (isError || !wopiInfo) {
    return <ErrorPreview file={item} />;
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
        <input
          name="access_token"
          value={wopiInfo.access_token}
          type="hidden"
        />
        <input
          name="access_token_ttl"
          value={wopiInfo.access_token_ttl}
          type="hidden"
        />
      </form>
      <iframe
        name="office_frame"
        className="wopi-editor-iframe"
        title={item.title}
      />
    </div>
  );
};
