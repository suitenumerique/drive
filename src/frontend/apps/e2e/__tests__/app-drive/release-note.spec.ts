import { expect, test } from "@playwright/test";
import { login } from "./utils-common";

const CURRENT_VERSION = "0.11.1";

test.describe("Release Note", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "drive@example.com");
  });

  test.describe("Feature flag", () => {
    test("should display release note modal when FRONTEND_RELEASE_NOTE_ENABLED is true", async ({
      page,
    }) => {
      await page.route("**/api/v1.0/config/", async (route) => {
        const response = await route.fetch();
        const json = await response.json();
        json.FRONTEND_RELEASE_NOTE_ENABLED = true;
        await route.fulfill({ response, json });
      });

      // Mock user with no last_release_note_seen
      await page.route("**/api/v1.0/users/me/", async (route) => {
        const response = await route.fetch();
        const json = await response.json();
        json.last_release_note_seen = null;
        await route.fulfill({ response, json });
      });

      await page.goto("/");
      await expect(page.getByText("Updates to Drive")).toBeVisible();
    });

    test("should NOT display release note modal when FRONTEND_RELEASE_NOTE_ENABLED is false", async ({
      page,
    }) => {
      await page.route("**/api/v1.0/config/", async (route) => {
        const response = await route.fetch();
        const json = await response.json();
        json.FRONTEND_RELEASE_NOTE_ENABLED = false;
        await route.fulfill({ response, json });
      });

      await page.goto("/");
      await expect(
        page.getByRole("button", { name: "Open user menu" }),
      ).toBeVisible();
      await expect(
        page.getByText("Updates to Drive"),
      ).not.toBeVisible();
    });
  });

  test.describe("Version comparison", () => {
    test.beforeEach(async ({ page }) => {
      // Ensure feature flag is disabled (release note visible)
      await page.route("**/api/v1.0/config/", async (route) => {
        const response = await route.fetch();
        const json = await response.json();
        json.FRONTEND_RELEASE_NOTE_ENABLED = true;
        await route.fulfill({ response, json });
      });
    });

    test("should display release note when user has not seen any version", async ({
      page,
    }) => {
      await page.route("**/api/v1.0/users/me/", async (route) => {
        const response = await route.fetch();
        const json = await response.json();
        json.last_release_note_seen = null;
        await route.fulfill({ response, json });
      });

      await page.goto("/");
      await expect(page.getByText("Updates to Drive")).toBeVisible();
    });

    test("should display release note when user has seen an older version", async ({
      page,
    }) => {
      await page.route("**/api/v1.0/users/me/", async (route) => {
        const response = await route.fetch();
        const json = await response.json();
        json.last_release_note_seen = "0.10.0"; // Older version
        await route.fulfill({ response, json });
      });

      await page.goto("/");
      await expect(page.getByText("Updates to Drive")).toBeVisible();
    });

    test("should NOT display release note when user has already seen current version", async ({
      page,
    }) => {
      await page.route("**/api/v1.0/users/me/", async (route) => {
        const response = await route.fetch();
        const json = await response.json();
        json.last_release_note_seen = CURRENT_VERSION;
        await route.fulfill({ response, json });
      });

      await page.goto("/");
      await expect(
        page.getByRole("button", { name: "Open user menu" }),
      ).toBeVisible();
      await expect(
        page.getByText("Updates to Drive"),
      ).not.toBeVisible();
    });
  });
});
