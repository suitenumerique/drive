import { useMemo, useEffect, useRef } from "react";
import { useQueries } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { Item, ItemUploadState } from "@/features/drivers/types";
import { useRefreshItemCache } from "./useRefreshItems";

const POLL_INTERVAL = 3000;
const POLL_TIMEOUT = 10 * 60 * 1000;

export const useDuplicatingItemsPoller = (items: Item[]) => {
  const refreshItemCache = useRefreshItemCache();
  const startTimesRef = useRef<Map<string, number>>(new Map());

  const duplicatingItems = useMemo(
    () => items.filter((i) => i.upload_state === ItemUploadState.DUPLICATING),
    [items],
  );

  useEffect(() => {
    for (const item of duplicatingItems) {
      if (!startTimesRef.current.has(item.id)) {
        startTimesRef.current.set(item.id, Date.now());
      }
    }
    const duplicatingIds = new Set(duplicatingItems.map((i) => i.id));
    for (const id of startTimesRef.current.keys()) {
      if (!duplicatingIds.has(id)) {
        startTimesRef.current.delete(id);
      }
    }
  }, [duplicatingItems]);

  useQueries({
    queries: duplicatingItems.map((item) => ({
      queryKey: ["items", item.id, "duplicate-poll"],
      queryFn: async () => {
        const updatedItem = await getDriver().getItem(item.id);
        if (updatedItem.upload_state !== ItemUploadState.DUPLICATING) {
          await refreshItemCache(item.id, updatedItem);
        }
        return updatedItem;
      },
      refetchInterval: (query: { state: { data: Item | undefined } }) => {
        const data = query.state.data;
        if (data && data.upload_state !== ItemUploadState.DUPLICATING) {
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
