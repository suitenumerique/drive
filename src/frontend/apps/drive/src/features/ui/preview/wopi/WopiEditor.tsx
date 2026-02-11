import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { FilePreviewType } from "../files-preview/FilesPreview";
import { ErrorPreview } from "../error/ErrorPreview";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useConfig } from "@/features/config/ConfigProvider";
import { getOperationTimeBound } from "@/features/operations/timeBounds";
import { useTimeBoundedPhase } from "@/features/operations/useTimeBoundedPhase";

interface WopiEditorProps {
  item: FilePreviewType;
}

export const WopiEditor = ({ item }: WopiEditorProps) => {
  const { t } = useTranslation();
  const { config } = useConfig();
  const formRef = useRef<HTMLFormElement>(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);

  const wopiInfoBounds = useMemo(
    () => getOperationTimeBound("wopi_info", config),
    [config],
  );
  const wopiIframeBounds = useMemo(
    () => getOperationTimeBound("wopi_iframe", config),
    [config],
  );

  const {
    data: wopiInfo,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["item", item.id, "wopi"],
    refetchOnWindowFocus: false,
    queryFn: () => getDriver().getWopiInfo(item.id),
  });

  useEffect(() => {
    if (wopiInfo && formRef.current) {
      setIframeLoaded(false);
      formRef.current.submit();
    }
  }, [wopiInfo]);

  const infoPhase = useTimeBoundedPhase(isLoading, wopiInfoBounds);
  const iframePhase = useTimeBoundedPhase(
    Boolean(wopiInfo) && !iframeLoaded,
    wopiIframeBounds,
  );

  if (isLoading) {
    if (infoPhase === "loading") {
      return <div>{t("file_preview.wopi.loading")}</div>;
    }

    return (
      <div>
        <div>
          {infoPhase === "still_working"
            ? t("operations.long_running.still_working")
            : t("operations.long_running.failed")}
        </div>
        <Button variant="tertiary" onClick={() => refetch()}>
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  if (isError || !wopiInfo) {
    return (
      <div>
        <div>{t("operations.long_running.failed")}</div>
        <Button variant="tertiary" onClick={() => refetch()}>
          {t("common.retry")}
        </Button>
        <ErrorPreview file={item} />
      </div>
    );
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
        key={iframeKey}
        name="office_frame"
        className="wopi-editor-iframe"
        title={item.title}
        onLoad={() => setIframeLoaded(true)}
      />
      {!iframeLoaded && (
        <div>
          {iframePhase === "loading" ? (
            <div>{t("file_preview.wopi.loading")}</div>
          ) : iframePhase === "still_working" ? (
            <div>{t("operations.long_running.still_working")}</div>
          ) : (
            <div>
              <div>{t("operations.long_running.failed")}</div>
              <Button
                variant="tertiary"
                onClick={() => {
                  setIframeKey((k) => k + 1);
                  refetch();
                }}
              >
                {t("common.retry")}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
