import { useCallback } from "react";
import { useModals } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";

const SAFE_PROTOCOLS = ["https:", "http:"];

export const useRedirectDisclaimer = () => {
  const modals = useModals();
  const { t } = useTranslation();
  const handlePdfClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement;
      const anchor = target.closest("a");
      if (anchor && anchor.href) {
        if (anchor.closest("[data-internal-link]")) return;

        e.preventDefault();
        e.stopPropagation();

        try {
          const url = new URL(anchor.href);
          if (!SAFE_PROTOCOLS.includes(url.protocol)) return;
        } catch {
          return;
        }

        modals.confirmationModal({
          title: t("file_preview.external_link.title"),
          children: (
            <div>
              <p>{t("file_preview.external_link.description")}</p>
              <pre className="pdf-preview__external-link">{anchor.href}</pre>
              <p>{t("file_preview.external_link.confirm_question")}</p>
            </div>
          ),
          onDecide: (decision) => {
            if (decision === "yes") {
              window.open(anchor.href, "_blank", "noopener,noreferrer");
            }
          },
        });
      }
    },
    [modals, t],
  );
  return { handlePdfClick };
};
