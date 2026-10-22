import { HeaderBannerConfig, LocalizedText } from "@/features/drivers/types";

export type HeaderBannerColor = NonNullable<HeaderBannerConfig["color"]>;

export type ResolvedHeaderBanner = {
  id?: string;
  color: HeaderBannerColor;
  label: string;
  cta?: {
    label: string;
    href: string;
    target?: string;
  };
};

const COLORS: HeaderBannerColor[] = ["brand", "warning", "error"];

export const dismissedStorageKey = (id: string) =>
  `header-banner-dismissed:${id}`;

/**
 * Returns the text for the given language, falling back to `default`.
 */
export const resolveLocalizedText = (
  text: LocalizedText | undefined,
  language: string,
): string | undefined => {
  if (typeof text === "string") {
    return text || undefined;
  }
  if (!text || typeof text !== "object") {
    return undefined;
  }
  return text[language] || text.default || undefined;
};

/**
 * Turns the FRONTEND_HEADER_BANNER setting into the props to display, or
 * undefined when there is nothing to display.
 */
export const resolveHeaderBanner = (
  config: HeaderBannerConfig | undefined,
  language: string,
): ResolvedHeaderBanner | undefined => {
  if (!config || typeof config !== "object") {
    return undefined;
  }

  const label = resolveLocalizedText(config.label, language);
  if (!label) {
    return undefined;
  }

  const ctaLabel = resolveLocalizedText(config.cta?.label, language);
  const ctaHref = config.cta?.href;

  return {
    id: config.id || undefined,
    color:
      config.color && COLORS.includes(config.color) ? config.color : "brand",
    label,
    cta:
      ctaLabel && ctaHref
        ? { label: ctaLabel, href: ctaHref, target: config.cta?.target }
        : undefined,
  };
};
