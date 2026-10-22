import { expect, Page, test } from "@playwright/test";
import { login } from "./utils-common";

const HEADER_BANNER = {
  id: "maintenance-e2e",
  color: "warning",
  label: {
    default: "An update is scheduled today at 1 p.m.",
    fr: "Une mise à jour est prévue aujourd'hui à 13h.",
  },
  cta: {
    label: { default: "Read more", fr: "En savoir plus" },
    href: "https://status.example.com/",
    target: "_blank",
  },
};

/**
 * Overrides FRONTEND_HEADER_BANNER in the config API response. The value is
 * read on each request, so tests can change it between page loads.
 */
const overrideHeaderBanner = async (
  page: Page,
  getHeaderBanner: () => unknown,
) => {
  await page.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    const headerBanner = getHeaderBanner();
    if (headerBanner === undefined) {
      delete json.FRONTEND_HEADER_BANNER;
    } else {
      json.FRONTEND_HEADER_BANNER = headerBanner;
    }
    await route.fulfill({ response, json });
  });
};

// The ui-kit names the banner region "Announcement" ("Annonce" in French).
const getBanner = (page: Page, name = "Announcement") =>
  page.getByRole("region", { name });

test.describe("Header banner", () => {
  test("is not displayed when not configured", async ({ page }) => {
    await overrideHeaderBanner(page, () => undefined);
    await login(page, "drive@example.com");
    await page.goto("/");

    // The user menu confirms the layout has loaded before asserting absence.
    await expect(page.getByRole("button", { name: "User menu" })).toBeVisible();
    await expect(page.locator(".c__header-banner")).toHaveCount(0);
    // The banner space must not be reserved either.
    await expect(page.locator(".c__main-layout__banner")).toHaveCount(0);
  });

  test("is displayed on the home page", async ({ page }) => {
    await overrideHeaderBanner(page, () => HEADER_BANNER);
    await page.goto("/");

    const banner = getBanner(page);
    await expect(banner).toBeVisible();
    await expect(banner).toHaveClass(/c__header-banner--warning/);
    await expect(banner).toContainText(HEADER_BANNER.label.default);
    await expect(
      banner.getByRole("link", { name: /Read more/ }),
    ).toHaveAttribute("href", HEADER_BANNER.cta.href);
  });

  test("is displayed in the explorer", async ({ page }) => {
    await overrideHeaderBanner(page, () => HEADER_BANNER);
    await login(page, "drive@example.com");
    await page.goto("/");

    await expect(page.getByRole("button", { name: "User menu" })).toBeVisible();
    await expect(getBanner(page)).toContainText(HEADER_BANNER.label.default);
  });

  test("stays closed until its id changes", async ({ page }) => {
    let headerBanner = HEADER_BANNER;
    await overrideHeaderBanner(page, () => headerBanner);
    await login(page, "drive@example.com");
    await page.goto("/");

    const banner = getBanner(page);
    await expect(banner).toBeVisible();
    await banner.getByRole("button", { name: "Close" }).click();
    await expect(page.locator(".c__header-banner")).toHaveCount(0);
    await expect(page.locator(".c__main-layout__banner")).toHaveCount(0);

    // Still closed after a reload.
    await page.reload();
    await expect(page.getByRole("button", { name: "User menu" })).toBeVisible();
    await expect(page.locator(".c__header-banner")).toHaveCount(0);

    // A new id shows the banner again.
    headerBanner = { ...HEADER_BANNER, id: "maintenance-e2e-2" };
    await page.reload();
    await expect(getBanner(page)).toBeVisible();
  });

  test("cannot be closed without an id", async ({ page }) => {
    await overrideHeaderBanner(page, () => ({ ...HEADER_BANNER, id: undefined }));
    await page.goto("/");

    const banner = getBanner(page);
    await expect(banner).toBeVisible();
    await expect(banner.getByRole("button", { name: "Close" })).toHaveCount(0);
  });

  test.describe("in French", () => {
    test.use({ locale: "fr-FR" });

    test("displays the translated texts", async ({ page }) => {
      await overrideHeaderBanner(page, () => HEADER_BANNER);
      // No login: the home page language comes from the browser.
      await page.goto("/");

      const banner = getBanner(page, "Annonce");
      await expect(banner).toContainText(HEADER_BANNER.label.fr);
      await expect(
        banner.getByRole("link", { name: /En savoir plus/ }),
      ).toBeVisible();
    });
  });
});
