export const WOPI_TAB_PATH = "/wopi";

export const openWopiInNewTab = (itemId: string): void => {
  window.open(
    `${WOPI_TAB_PATH}/${encodeURIComponent(itemId)}`,
    "_blank",
    "noopener,noreferrer",
  );
};
