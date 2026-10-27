import { Checkmark2, ErrorFilled } from "@gouvfr-lasuite/ui-components/icons";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useCallback } from "react";
import { useTranslation } from "react-i18next";

export const useClipboard = () => {
  const { t } = useTranslation();

  return useCallback(
    (text: string, successMessage?: string, errorMessage?: string) => {
      navigator.clipboard
        .writeText(text)
        .then(() => {
          addToast(
            <ToasterItem>
              <Checkmark2 aria-hidden="true" />
              <span>{successMessage ?? t("clipboard.success")}</span>
            </ToasterItem>
          );
        })
        .catch(() => {
          addToast(
            <ToasterItem type="error">
              <ErrorFilled aria-hidden="true" />
              <span>{errorMessage ?? t("clipboard.error")}</span>
            </ToasterItem>
          );
        });
    },
    [t]
  );
};
