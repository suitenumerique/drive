import { DEFAULT_CONFIG } from "./Config";
import { Item } from "./Types";

export const openPicker = (
  customConfig?: Partial<typeof DEFAULT_CONFIG>,
  onFailure?: () => void
): Promise<{
  items: Item[];
}> => {
  const config = { ...DEFAULT_CONFIG, ...customConfig };

  const popupWindow = window.open(
    `${config.url}`,
    "CreatePopupWindow",
    `status=no,location=no,toolbar=no,menubar=no,width=1300,height=600,left=100,top=100, resizable=yes,scrollbars=yes`
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

      if (type === "items-selected") {
        console.log("ITEMS SELECTED", data);
        window.removeEventListener("message", onMessage);
        resolve(data);
        popupWindow?.close();
      }
    };

    window.addEventListener("message", onMessage);
  });
};
