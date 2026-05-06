import { FilePreviewType } from "@gouvfr-lasuite/ui-kit";

export const WOPI_TAB_PATH = "/wopi";

export const openWopiInNewTab = (item: FilePreviewType): void => {
  window.open(
    `${WOPI_TAB_PATH}/${encodeURIComponent(item.id)}`,
    "_blank",
    "noopener,noreferrer",
  );
};
