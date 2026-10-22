import { HeaderBanner } from "@gouvfr-lasuite/ui-components";
import { ReactNode, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { splitLocaleCode } from "@/features/i18n/utils";
import { useAnnouncements } from "./useAnnouncements";
import { dismissedStorageKey, resolveHeaderBanner } from "./utils";

const isDismissedInStorage = (id: string | undefined) => {
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
 * Builds the header banner announcement, to pass to the `topBanner` prop of
 * MainLayout.
 *
 * This is a hook rather than a component on purpose: MainLayout reserves the
 * banner space as soon as `topBanner` is truthy, so it must receive undefined,
 * not a component rendering null, when there is nothing to display.
 */
export const useHeaderBannerAnnouncement = (): ReactNode => {
  const { data: announcements } = useAnnouncements();
  const { i18n } = useTranslation();
  const banner = resolveHeaderBanner(
    announcements,
    splitLocaleCode(i18n.language).language,
  );
  // Banners closed during this visit, in case localStorage is not available.
  const [closedIds, setClosedIds] = useState<string[]>([]);
  const isDismissed = useMemo(
    () => isDismissedInStorage(banner?.isDismissible ? banner.id : undefined),
    [banner?.id, banner?.isDismissible],
  );

  if (
    !banner ||
    (banner.isDismissible && (isDismissed || closedIds.includes(banner.id)))
  ) {
    return undefined;
  }

  const onClose = banner.isDismissible
    ? () => {
        try {
          localStorage.setItem(dismissedStorageKey(banner.id), "1");
        } catch {
          // Still hidden until the next page load.
        }
        setClosedIds((ids) => [...ids, banner.id]);
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
