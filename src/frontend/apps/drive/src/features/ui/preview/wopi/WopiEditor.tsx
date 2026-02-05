import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { FilePreviewType } from "../files-preview/FilesPreview";
import { ErrorPreview } from "../error/ErrorPreview";

interface WopiEditorProps {
  item: FilePreviewType;
  onFileRename?: (file: FilePreviewType, newName: string) => void;
}

export const WopiEditor = ({ item, onFileRename }: WopiEditorProps) => {
  const { t } = useTranslation();
  const formRef = useRef<HTMLFormElement>(null);
  const queryClient = useQueryClient();

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

  // Listen for PostMessage events from the WOPI editor.
  // At the moment only OnlyOffice supports this feature as Collabora
  // does not post messages when renaming a file.
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      let data = event.data;
      if (typeof data === "string") {
        try {
          data = JSON.parse(data);
        } catch {
          return;
        }
      }

      if (!data || typeof data !== "object" || !data.MessageId) {
        return;
      }

      // Handle rename notifications from the WOPI editor
      if (data.MessageId === "File_Rename") {
        onFileRename?.(item, data.Values.NewName);
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [item.id, queryClient]);

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
