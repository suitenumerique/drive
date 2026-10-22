import { expect, Page, test } from "@playwright/test";
import { login, runFixture } from "./utils-common";

// Published by the e2e_fixture_announcements command
const BODY = {
  en: "An update is scheduled today at 1 p.m.",
  fr: "Une mise à jour est prévue aujourd'hui à 13h.",
};
const CTA_URL = "https://status.example.com/";

// The ui-kit names the banner region "Announcement" ("Annonce" in French).
const getBanner = (page: Page, name = "Announcement") =>
  page.getByRole("region", { name });

test.describe("Header banner announcements", () => {
  test.beforeEach(async () => {
    await runFixture("e2e_fixture_announcements");
  });

  // Do not leak the banner into the other tests.
  test.afterAll(async () => {
    await runFixture("e2e_fixture_announcements none");
  });

  test("is displayed on the home page", async ({ page }) => {
    await page.goto("/");

    const banner = getBanner(page);
    await expect(banner).toBeVisible();
    await expect(banner).toHaveClass(/c__header-banner--warning/);
    await expect(banner).toContainText(BODY.en);
    await expect(
      banner.getByRole("link", { name: /Read more/ }),
    ).toHaveAttribute("href", CTA_URL);
  });

  test("is displayed in the explorer", async ({ page }) => {
    await login(page, "drive@example.com");
    await page.goto("/");

    await expect(page.getByRole("button", { name: "User menu" })).toBeVisible();
    await expect(getBanner(page)).toContainText(BODY.en);
  });

  test("stays closed until a new announcement is published", async ({
    page,
  }) => {
    await login(page, "drive@example.com");
    await page.goto("/");

    const banner = getBanner(page);
    await banner.getByRole("button", { name: "Close" }).click();
    await expect(page.locator(".c__header-banner")).toHaveCount(0);
    // The banner space is not reserved anymore.
    await expect(page.locator(".c__main-layout__banner")).toHaveCount(0);

    await page.reload();
    await expect(page.getByRole("button", { name: "User menu" })).toBeVisible();
    await expect(page.locator(".c__header-banner")).toHaveCount(0);

    // The fixture publishes it again as a new announcement.
    await runFixture("e2e_fixture_announcements");
    await page.reload();
    await expect(getBanner(page)).toContainText(BODY.en);
  });

  test("cannot be closed when not dismissible", async ({ page }) => {
    await runFixture("e2e_fixture_announcements not_dismissible");
    await page.goto("/");

    const banner = getBanner(page);
    await expect(banner).toBeVisible();
    await expect(banner.getByRole("button", { name: "Close" })).toHaveCount(0);
  });

  test("is not displayed without announcements", async ({ page }) => {
    await runFixture("e2e_fixture_announcements none");
    await login(page, "drive@example.com");
    await page.goto("/");

    await expect(page.getByRole("button", { name: "User menu" })).toBeVisible();
    await expect(page.locator(".c__header-banner")).toHaveCount(0);
    await expect(page.locator(".c__main-layout__banner")).toHaveCount(0);
  });

  test.describe("in French", () => {
    test.use({ locale: "fr-FR" });

    test("displays the translated texts", async ({ page }) => {
      // No login: the home page language comes from the browser.
      await page.goto("/");

      const banner = getBanner(page, "Annonce");
      await expect(banner).toContainText(BODY.fr);
      await expect(
        banner.getByRole("link", { name: /En savoir plus/ }),
      ).toBeVisible();
    });
  });
});
