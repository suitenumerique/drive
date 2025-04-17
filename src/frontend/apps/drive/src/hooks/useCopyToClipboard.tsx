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
              <span className="material-icons">check</span>
              <span>{successMessage ?? t("clipboard.success")}</span>
            </ToasterItem>
          );
        })
        .catch(() => {
          addToast(
            <ToasterItem type="error">
              <span className="material-icons">error</span>
              <span>{errorMessage ?? t("clipboard.error")}</span>
            </ToasterItem>
          );
        });
    },
    [t]
  );
};
