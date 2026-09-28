import { expect, test } from "@playwright/test";
import { login } from "./utils-common";

test.describe("Custom CSS and JS injection", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "drive@example.com");
  });

  test("should inject a stylesheet link when FRONTEND_CSS_URL is set", async ({
    page,
  }) => {
    const cssUrl = "https://example.com/custom.css";

    await page.route("**/api/v1.0/config/", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.FRONTEND_CSS_URL = cssUrl;
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "User menu" }),
    ).toBeVisible();

    const linkEl = page.locator(`link[rel="stylesheet"][href="${cssUrl}"]`);
    await expect(linkEl).toBeAttached();
  });

  test("should NOT inject a stylesheet link when FRONTEND_CSS_URL is not set", async ({
    page,
  }) => {
    await page.route("**/api/v1.0/config/", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      delete json.FRONTEND_CSS_URL;
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "User menu" }),
    ).toBeVisible();

    const linkEl = page.locator(
      'link[rel="stylesheet"][href="https://example.com/custom.css"]',
    );
    await expect(linkEl).not.toBeAttached();
  });

  test("should inject a script tag when FRONTEND_JS_URL is set", async ({
    page,
  }) => {
    const jsUrl = "https://example.com/custom.js";

    await page.route("**/api/v1.0/config/", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.FRONTEND_JS_URL = jsUrl;
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "User menu" }),
    ).toBeVisible();

    const scriptEl = page.locator(`script[src="${jsUrl}"]`);
    await expect(scriptEl).toBeAttached();
  });

  test("should NOT inject a script tag when FRONTEND_JS_URL is not set", async ({
    page,
  }) => {
    await page.route("**/api/v1.0/config/", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      delete json.FRONTEND_JS_URL;
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "User menu" }),
    ).toBeVisible();

    const scriptEl = page.locator(
      'script[src="https://example.com/custom.js"]',
    );
    await expect(scriptEl).not.toBeAttached();
  });
});
