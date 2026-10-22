import {
  dismissedStorageKey,
  resolveHeaderBanner,
  resolveLocalizedText,
} from "../utils";

describe("resolveLocalizedText", () => {
  it("returns a plain string as is", () => {
    expect(resolveLocalizedText("Hello", "fr")).toBe("Hello");
  });

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
    expect(resolveLocalizedText(undefined, "en")).toBeUndefined();
    expect(resolveLocalizedText("", "en")).toBeUndefined();
  });
});

describe("resolveHeaderBanner", () => {
  it("returns undefined when nothing is configured", () => {
    expect(resolveHeaderBanner(undefined, "en")).toBeUndefined();
    expect(resolveHeaderBanner({}, "en")).toBeUndefined();
  });

  it("returns undefined when there is no label for the language", () => {
    expect(
      resolveHeaderBanner({ label: { default: "", fr: "Bonjour" } }, "en"),
    ).toBeUndefined();
  });

  it("resolves a full banner", () => {
    expect(
      resolveHeaderBanner(
        {
          id: "maintenance",
          color: "warning",
          label: { default: "Maintenance", fr: "Maintenance FR" },
          cta: {
            label: { default: "Read more", fr: "En savoir plus" },
            href: "https://status.example.com",
            target: "_blank",
          },
        },
        "fr",
      ),
    ).toEqual({
      id: "maintenance",
      color: "warning",
      label: "Maintenance FR",
      cta: {
        label: "En savoir plus",
        href: "https://status.example.com",
        target: "_blank",
      },
    });
  });

  it("defaults to the brand color when the color is unknown", () => {
    expect(
      resolveHeaderBanner(
        // @ts-expect-error unknown color coming from the settings
        { label: "Hello", color: "pink" },
        "en",
      )?.color,
    ).toBe("brand");
  });

  it("drops an incomplete call to action", () => {
    expect(
      resolveHeaderBanner(
        { label: "Hello", cta: { label: "Read more" } },
        "en",
      )?.cta,
    ).toBeUndefined();
    expect(
      resolveHeaderBanner(
        { label: "Hello", cta: { href: "https://example.com" } },
        "en",
      )?.cta,
    ).toBeUndefined();
  });

  it("is not closable without an id", () => {
    expect(resolveHeaderBanner({ label: "Hello" }, "en")?.id).toBeUndefined();
  });
});

describe("dismissedStorageKey", () => {
  it("includes the banner id", () => {
    expect(dismissedStorageKey("maintenance")).toBe(
      "header-banner-dismissed:maintenance",
    );
  });
});
