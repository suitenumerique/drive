import { HeaderBanner } from "@gouvfr-lasuite/ui-components";
import { ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { useConfig } from "@/features/config/ConfigProvider";
import { splitLocaleCode } from "@/features/i18n/utils";
import { dismissedStorageKey, resolveHeaderBanner } from "./utils";

const isDismissed = (id: string | undefined) => {
  if (!id) {
    return false;
  }
  try {
    return localStorage.getItem(dismissedStorageKey(id)) !== null;
  } catch {
    return false;
  }
};

/**
 * Builds the banner configured with FRONTEND_HEADER_BANNER, to pass to the
 * `topBanner` prop of MainLayout.
 *
 * This is a hook rather than a component on purpose: MainLayout reserves the
 * banner space as soon as `topBanner` is truthy, so it must receive undefined,
 * not a component rendering null, when there is nothing to display.
 */
export const useConfigHeaderBanner = (): ReactNode => {
  const { config } = useConfig();
  const { i18n } = useTranslation();
  const banner = resolveHeaderBanner(
    config.FRONTEND_HEADER_BANNER,
    splitLocaleCode(i18n.language).language,
  );
  const [dismissedId, setDismissedId] = useState<string | undefined>(() =>
    isDismissed(banner?.id) ? banner?.id : undefined,
  );

  if (!banner || (banner.id && banner.id === dismissedId)) {
    return undefined;
  }

  const id = banner.id;
  const onClose = id
    ? () => {
        try {
          localStorage.setItem(dismissedStorageKey(id), "1");
        } catch {
          // The banner is still hidden until the next page load.
        }
        setDismissedId(id);
      }
    : undefined;

  return (
    <HeaderBanner
      color={banner.color}
      label={banner.label}
      ctaProps={banner.cta}
      onClose={onClose}
    />
  );
};
