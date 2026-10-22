import {
  Announcement,
  AnnouncementLevel,
  LocalizedText,
} from "@/features/drivers/types";

export const HEADER_BANNER_DISPLAY = "header_banner";

export type HeaderBannerColor = "brand" | "warning" | "error";

export type ResolvedHeaderBanner = {
  id: string;
  color: HeaderBannerColor;
  label: string;
  isDismissible: boolean;
  cta?: {
    label: string;
    href: string;
    target?: string;
  };
};

const LEVEL_COLORS: Record<AnnouncementLevel, HeaderBannerColor> = {
  info: "brand",
  warning: "warning",
  error: "error",
};

export const dismissedStorageKey = (id: string) =>
  `announcement-dismissed:${id}`;

/**
 * Returns the text for the given language, falling back to `default`.
 */
export const resolveLocalizedText = (
  text: LocalizedText | null | undefined,
  language: string,
): string | undefined => {
  if (!text) {
    return undefined;
  }
  return text[language] || text.default || undefined;
};

/**
 * Returns the props of the header banner to display: the first header banner
 * announcement, as they are sorted by priority. Undefined when there is none.
 */
export const resolveHeaderBanner = (
  announcements: Announcement[] | undefined,
  language: string,
): ResolvedHeaderBanner | undefined => {
  const announcement = announcements?.find(
    ({ display }) => display === HEADER_BANNER_DISPLAY,
  );
  if (!announcement) {
    return undefined;
  }

  const label = resolveLocalizedText(announcement.body, language);
  if (!label) {
    return undefined;
  }

  const ctaLabel = resolveLocalizedText(announcement.cta?.label, language);
  return {
    id: announcement.id,
    color: LEVEL_COLORS[announcement.level] ?? "brand",
    label,
    isDismissible: announcement.is_dismissible,
    cta:
      announcement.cta && ctaLabel
        ? {
            label: ctaLabel,
            href: announcement.cta.url,
            target: announcement.cta.new_tab ? "_blank" : undefined,
          }
        : undefined,
  };
};
