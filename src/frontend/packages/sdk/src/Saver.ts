import { DEFAULT_CONFIG } from "./Config";
import { ClientMessageType } from "./Types";

interface FileSavePayload {
  title: string;
  object: File;
}

interface SaverPayload {
  files: FileSavePayload[];
}

export const openSaver = (
  payload: SaverPayload,
  customConfig?: Partial<typeof DEFAULT_CONFIG>,
  onFailure?: () => void
) => {
  const config = { ...DEFAULT_CONFIG, ...customConfig };

  const popupWindow = window.open(
    `${config.url}?mode=save`,
    "CreatePopupWindow",
    `popup=yes,status=no,location=no,toolbar=no,menubar=no,width=1300,height=600,left=100,top=100, resizable=yes,scrollbars=yes`
  );

  if (popupWindow) {
    popupWindow.focus();
  } else {
    onFailure?.();
  }

  return new Promise((resolve) => {
    const onMessage = (event: MessageEvent) => {
      // Make sure it is the correct origin.
      if (event.origin !== new URL(config.url).origin) {
        return;
      }

      const { type, data } = event.data;

      switch (type) {
        case ClientMessageType.SAVER_READY:
          popupWindow?.postMessage(
            {
              type: ClientMessageType.SAVER_PAYLOAD,
              data: payload,
            },
            "*"
          );
          break;
        case ClientMessageType.ITEM_SAVED:
          window.removeEventListener("message", onMessage);
          resolve(data);
          popupWindow?.close();
          break;
      }
    };

    window.addEventListener("message", onMessage);
  });
};
