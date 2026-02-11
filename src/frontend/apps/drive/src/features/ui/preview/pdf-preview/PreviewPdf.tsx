import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useConfig } from "@/features/config/ConfigProvider";
import { getOperationTimeBound } from "@/features/operations/timeBounds";
import { useTimeBoundedPhase } from "@/features/operations/useTimeBoundedPhase";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

interface PreviewPdfProps {
  src?: string;
}

export const PreviewPdf = ({ src }: PreviewPdfProps) => {
  const { t } = useTranslation();
  const { config } = useConfig();
  const bounds = useMemo(
    () => getOperationTimeBound("preview_pdf", config),
    [config],
  );
  const [loaded, setLoaded] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const phase = useTimeBoundedPhase(Boolean(src) && !loaded, bounds);

  useEffect(() => {
    setLoaded(false);
    setReloadKey((k) => k + 1);
  }, [src]);

  return (
    <div>
      <iframe
        key={reloadKey}
        src={src}
        width="100%"
        height="100%"
        className="pdf-container__iframe"
        onLoad={() => setLoaded(true)}
      />
      {!loaded && src && (
        <div>
          {phase === "loading" ? (
            <div>{t("file_preview.wopi.loading")}</div>
          ) : phase === "still_working" ? (
            <div>{t("operations.long_running.still_working")}</div>
          ) : (
            <div>
              <div>{t("operations.long_running.failed")}</div>
              <Button
                variant="tertiary"
                onClick={() => {
                  setLoaded(false);
                  setReloadKey((k) => k + 1);
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
