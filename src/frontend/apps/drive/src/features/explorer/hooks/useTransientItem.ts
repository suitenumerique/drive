import { useTranslation } from "react-i18next";
import {
  Item,
  ItemUploadState,
  TRANSIENT_UPLOAD_STATES,
} from "@/features/drivers/types";

export type TransientItem = {
  isTransient: boolean;
  label: string | null;
};

export const useTransientItem = (item: Item): TransientItem => {
  const { t } = useTranslation();
  const isTransient = TRANSIENT_UPLOAD_STATES.includes(item.upload_state);
  const transientLabels: Record<string, string> = {
    [ItemUploadState.CONVERTING]: t("explorer.item.converting"),
    [ItemUploadState.DUPLICATING]: t("explorer.item.duplicating"),
  };
  const label = transientLabels[item.upload_state] ?? null;
  return { isTransient, label };
};
