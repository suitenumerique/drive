import { DEFAULT_CONFIG } from "./Config";
import { ClientMessageType, Item, SDKRelayEvent } from "./Types";
import { randomToken } from "./utils";

export const openPicker = async (
  customConfig?: Partial<typeof DEFAULT_CONFIG>,
  onFailure?: () => void
): Promise<{
  items: Item[];
}> => {
  const config = { ...DEFAULT_CONFIG, ...customConfig };

  const token = randomToken();

  const popupWindow = window.open(
    `${config.url}?token=${token}`,
    "CreatePopupWindow",
    `popup=yes,status=no,location=no,toolbar=no,menubar=no,width=1300,height=600,left=100,top=100, resizable=yes,scrollbars=yes`
  );

  if (popupWindow) {
    popupWindow.focus();
  } else {
    onFailure?.();
  }

  const result = await startPollingForEvent(config, token);

  if (result?.type === ClientMessageType.ITEMS_SELECTED) {
    return result.data;
  }

  console.error("Unexpected event", result);
  throw new Error("Unexpected event");
};

/**
 * Start polling for an event.
 * @param config - The config object.
 * @param token - The token to poll for.
 * @returns The event.
 */
const startPollingForEvent = (
  config: typeof DEFAULT_CONFIG,
  token: string
): Promise<SDKRelayEvent> => {
  return new Promise((resolve) => {
    const poll = async () => {
      const response = await fetch(
        `${config.apiUrl}/sdk-relay/events/${token}/`
      );
      const data = await response.json();
      console.log("Event", data);

      if (data?.type) {
        console.log("Event resolved", data);
        resolve(data);
        return;
      }
      setTimeout(poll, 2000);
    };

    // Start polling
    poll();
  });
};
