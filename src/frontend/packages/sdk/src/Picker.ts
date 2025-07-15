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
    `popup=yes,status=no,location=no,toolbar=no,menubar=no,width=1000,height=600,left=100,top=100, resizable=yes,scrollbars=yes`
  );

  if (popupWindow) {
    popupWindow.focus();
  } else {
    return {
      type: "cancelled",
    };
  }

  return new Promise((resolve) => {
    startPollingForEvent(config, token, (event) => {
      if (event?.type === ClientMessageType.ITEMS_SELECTED) {
        popupWindow?.close();
        resolve({
          type: "picked",
          items: event.data.items,
        });
      } else if (event?.type === ClientMessageType.CANCEL) {
        popupWindow?.close();
        resolve({
          type: "cancelled",
        });
      } else {
        console.error("Unexpected event", event);
        throw new Error("Unexpected event");
      }
    });

    // const { stop: stopWatchingForClosing } = watchForClosing(
    //   popupWindow,
    //   () => {
    //     log("Popup closed");
    //     stop();
    //     resolve({
    //       type: "cancelled",
    //     });
    //   }
    // );
  });
};

/*
 * This is not reliable in cases where the popup is redirected to a different domain.
 * In those cases, popupWindow.closed is true but the popup is still open.
 */
// const watchForClosing = (popupWindow: Window, onClosed: () => void) => {
//   let timeout: NodeJS.Timeout;
//   const check = () => {
//     if (popupWindow.closed) {
//       onClosed();
//       clearTimeout(timeout);
//     } else {
//       timeout = setTimeout(check, 100);
//     }
//   };

//   check();

//   return {
//     stop: () => {
//       log("Stop watching for closing");
//       clearTimeout(timeout);
//     },
//   };
// };

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
    interval = setTimeout(poll, 500);
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
