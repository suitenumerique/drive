import { useMemo, useEffect, useRef } from "react";
import { useQueries, useQueryClient } from "@tanstack/react-query";
import { APIError } from "@/features/api/APIError";
import { getDriver } from "@/features/config/Config";
import {
  Item,
  ItemUploadState,
  POLLED_UPLOAD_STATES,
} from "@/features/drivers/types";
import { useRefreshItemCache } from "./useRefreshItems";
import { useRemoveItemsFromPaginatedList } from "./useOptimisticPagination";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useTranslation } from "react-i18next";

const POLL_INTERVAL = 3000;
const POLL_TIMEOUT = 10 * 60 * 1000;

export const useTransientItemsPoller = (items: Item[]) => {
  const refreshItemCache = useRefreshItemCache();
  const removeItems = useRemoveItemsFromPaginatedList();
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  const startTimesRef = useRef<Map<string, number>>(new Map());
  const failedToastShownRef = useRef<Set<string>>(new Set());

  const transientItems = useMemo(
    () =>
      items.filter((i) => POLLED_UPLOAD_STATES.includes(i.upload_state)),
    [items],
  );

  useEffect(() => {
    for (const item of transientItems) {
      if (!startTimesRef.current.has(item.id)) {
        startTimesRef.current.set(item.id, Date.now());
      }
    }
    const transientIds = new Set(transientItems.map((i) => i.id));
    for (const id of startTimesRef.current.keys()) {
      if (!transientIds.has(id)) {
        startTimesRef.current.delete(id);
      }
    }
  }, [transientItems]);

  useQueries({
    queries: transientItems.map((item) => ({
      queryKey: ["items", item.id, "transient-poll"],
      queryFn: async (): Promise<Item | null> => {
        try {
          const updatedItem = await getDriver().getItem(item.id);
          if (!POLLED_UPLOAD_STATES.includes(updatedItem.upload_state)) {
            await refreshItemCache(item.id, updatedItem);
          }
          return updatedItem;
        } catch (error) {
          if (error instanceof APIError && error.code === 404) {
            removeItems(["items"], [item.id]);
            queryClient.removeQueries({ queryKey: ["items", item.id] });
            // Only a conversion placeholder vanishing is a failure worth a
            // toast; an analyzed item may simply have been deleted meanwhile.
            const isConverting =
              item.upload_state === ItemUploadState.CONVERTING;
            if (isConverting && !failedToastShownRef.current.has(item.id)) {
              failedToastShownRef.current.add(item.id);
              addToast(
                <ToasterItem type="error">
                  {t("explorer.actions.convert.modal.error")}
                </ToasterItem>
              );
            }
            return null;
          }
          throw error;
        }
      },
      refetchInterval: (query: {
        state: { data: Item | null | undefined };
      }) => {
        const data = query.state.data;
        if (data === null) {
          return false;
        }
        if (data && !POLLED_UPLOAD_STATES.includes(data.upload_state)) {
          return false;
        }
        const startTime = startTimesRef.current.get(item.id) ?? Date.now();
        if (Date.now() - startTime > POLL_TIMEOUT) {
          return false;
        }
        return POLL_INTERVAL;
      },
    })),
  });
};
