import { Announcement } from "@/features/drivers/types";
import {
  dismissedStorageKey,
  resolveHeaderBanner,
  resolveLocalizedText,
} from "../utils";

const announcement = (overrides: Partial<Announcement> = {}): Announcement => ({
  id: "1",
  display: "header_banner",
  level: "warning",
  title: null,
  body: { default: "Maintenance", fr: "Maintenance FR" },
  cta: {
    label: { default: "Read more", fr: "En savoir plus" },
    url: "https://status.example.com",
    new_tab: true,
  },
  is_dismissible: true,
  ...overrides,
});

describe("resolveLocalizedText", () => {
  it("returns the text for the given language", () => {
    expect(
      resolveLocalizedText({ default: "Hello", fr: "Bonjour" }, "fr"),
    ).toBe("Bonjour");
  });

  it("falls back to default when the language is missing", () => {
    expect(
      resolveLocalizedText({ default: "Hello", fr: "Bonjour" }, "de"),
    ).toBe("Hello");
  });

  it("returns undefined for empty values", () => {
    expect(resolveLocalizedText(null, "en")).toBeUndefined();
    expect(resolveLocalizedText({ default: "" }, "en")).toBeUndefined();
  });
});

describe("resolveHeaderBanner", () => {
  it("returns undefined without header banner announcements", () => {
    expect(resolveHeaderBanner(undefined, "en")).toBeUndefined();
    expect(resolveHeaderBanner([], "en")).toBeUndefined();
    expect(
      resolveHeaderBanner([announcement({ display: "modal" })], "en"),
    ).toBeUndefined();
  });

  it("resolves the first header banner, in the given language", () => {
    expect(
      resolveHeaderBanner(
        [
          announcement({ display: "modal", id: "0" }),
          announcement(),
          announcement({ id: "2" }),
        ],
        "fr",
      ),
    ).toEqual({
      id: "1",
      color: "warning",
      label: "Maintenance FR",
      isDismissible: true,
      cta: {
        label: "En savoir plus",
        href: "https://status.example.com",
        target: "_blank",
      },
    });
  });

  it("maps the levels to the banner colors", () => {
    expect(
      resolveHeaderBanner([announcement({ level: "info" })], "en")?.color,
    ).toBe("brand");
    expect(
      resolveHeaderBanner([announcement({ level: "error" })], "en")?.color,
    ).toBe("error");
  });

  it("opens the link in the same tab when asked", () => {
    expect(
      resolveHeaderBanner(
        [
          announcement({
            cta: {
              label: { default: "Read more" },
              url: "https://example.com",
              new_tab: false,
            },
          }),
        ],
        "en",
      )?.cta?.target,
    ).toBeUndefined();
  });

  it("has no link without a call to action", () => {
    expect(
      resolveHeaderBanner([announcement({ cta: null })], "en")?.cta,
    ).toBeUndefined();
  });
});

describe("dismissedStorageKey", () => {
  it("includes the announcement id", () => {
    expect(dismissedStorageKey("1")).toBe("announcement-dismissed:1");
  });
});
