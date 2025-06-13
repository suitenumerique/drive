import { DEFAULT_CONFIG } from "./Config";
import { ClientMessageType, Item, SDKRelayEvent } from "./Types";
import { randomToken } from "./utils";

export interface PickerResult {
  type: "picked" | "cancelled";
  items?: Item[];
}

export const openPicker = async (
  customConfig?: Partial<typeof DEFAULT_CONFIG>
): Promise<PickerResult> => {
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
    return {
      type: "cancelled",
    };
  }

  return new Promise((resolve) => {
    const { stop } = startPollingForEvent(config, token, (event) => {
      if (event?.type === ClientMessageType.ITEMS_SELECTED) {
        stopWatchingForClosing();
        popupWindow?.close();
        resolve({
          type: "picked",
          items: event.data.items,
        });
      } else {
        console.error("Unexpected event", event);
        throw new Error("Unexpected event");
      }
    });

    const { stop: stopWatchingForClosing } = watchForClosing(
      popupWindow,
      () => {
        console.log("Popup closed");
        stop();
        resolve({
          type: "cancelled",
        });
      }
    );
  });
};

const watchForClosing = (popupWindow: Window, onClosed: () => void) => {
  let timeout: NodeJS.Timeout;
  const check = () => {
    if (popupWindow.closed) {
      onClosed();
      clearTimeout(timeout);
    } else {
      timeout = setTimeout(check, 100);
    }
  };

  check();

  return {
    stop: () => {
      console.log("Stop watching for closing");
      clearTimeout(timeout);
    },
  };
};

/**
 * Start polling for an event.
 * @param config - The config object.
 * @param token - The token to poll for.
 * @returns The event.
 */
const startPollingForEvent = (
  config: typeof DEFAULT_CONFIG,
  token: string,
  onEvent: (event: SDKRelayEvent) => void
) => {
  let interval: NodeJS.Timeout;

  const poll = async () => {
    const response = await fetch(`${config.apiUrl}/sdk-relay/events/${token}/`);
    const data = await response.json();
    console.log("Event", data);

    if (data?.type) {
      console.log("Event resolved", data);
      onEvent(data);
      return;
    }
    interval = setTimeout(poll, 1000);
  };

  // Start polling
  poll();

  return {
    stop: () => {
      console.log("Stop polling");
      clearInterval(interval);
    },
  };
};
