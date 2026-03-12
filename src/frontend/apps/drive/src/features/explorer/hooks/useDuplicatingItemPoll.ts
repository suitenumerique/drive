import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import { Item, ItemUploadState } from "@/features/drivers/types";
import { useRefreshItemCache } from "./useRefreshItems";

const POLL_INTERVAL = 3000;
const POLL_TIMEOUT = 5 * 60 * 1000; // 5 minutes

export const useDuplicatingItemPoll = (item: Item) => {
  const isDuplicating = item.upload_state === ItemUploadState.DUPLICATING;
  const startTimeRef = useRef<number>(Date.now());
  const refreshItemCache = useRefreshItemCache();

  useEffect(() => {
    if (isDuplicating) {
      startTimeRef.current = Date.now();
    }
  }, [isDuplicating]);

  useQuery({
    queryKey: ["items", item.id, "duplicate-poll"],
    queryFn: async () => {
      const updatedItem = await getDriver().getItem(item.id);
      if (updatedItem.upload_state !== ItemUploadState.DUPLICATING) {
        await refreshItemCache(item.id, updatedItem);
      }
      return updatedItem;
    },
    enabled: isDuplicating,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.upload_state !== ItemUploadState.DUPLICATING) {
        return false;
      }
      if (Date.now() - startTimeRef.current > POLL_TIMEOUT) {
        return false;
      }
      return POLL_INTERVAL;
    },
  });
};
