import test from "@playwright/test";
import { login } from "./utils-common";
import {
  clickToFavorites,
  clickToMyFiles,
  clickToRecent,
  clickToSharedWithMe,
  clickToTrash,
} from "./utils-navigate";

test.describe("Left bar navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "drive@example.com");
    await page.goto("/");
  });

  test("Checks that the recents link in left bar redirects to the recents page", async ({
    page,
  }) => {
    await clickToRecent(page);
  });

  test("Checks that the my files link in left bar redirects to the my files page", async ({
    page,
  }) => {
    await clickToMyFiles(page);
  });

  test("Checks that the shared with me link in left bar redirects to the shared with me page", async ({
    page,
  }) => {
    await clickToSharedWithMe(page);
  });

  test("Checks that the trash link in left bar redirects to the trash page", async ({
    page,
  }) => {
    await clickToTrash(page);
  });

  test("Checks that the favorites link in left bar redirects to the favorites page", async ({
    page,
  }) => {
    await clickToFavorites(page);
  });
});
