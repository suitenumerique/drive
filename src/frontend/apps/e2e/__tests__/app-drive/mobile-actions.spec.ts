import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import { getRowItem } from "./utils-embedded-grid";

const MOBILE_VIEWPORT = { width: 375, height: 667 };

test.describe("Mobile actions menu", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
  });

  test("My Files shows more menu with create and import options", async ({
    page,
  }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await page.goto("/explorer/items/my-files");

    const moreButton = page.getByRole("button", { name: "more_vert" });
    await expect(moreButton).toBeVisible();
    await moreButton.click();

    await expect(
      page.getByRole("menuitem", { name: "New folder" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Import files" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Import folders" }),
    ).toBeVisible();
  });

  test("Folder shows more menu button", async ({ page }) => {
    // Create folder at desktop viewport where sidebar and buttons are available
    await page.goto("/");
    await clickToMyFiles(page);
    await createFolderInCurrentFolder(page, "TestFolder");

    // Get the folder URL
    const folderRow = await getRowItem(page, "TestFolder");
    await folderRow.dblclick();
    const folderUrl = page.url();

    // Switch to mobile and navigate to folder
    await page.setViewportSize(MOBILE_VIEWPORT);
    await page.goto(folderUrl);

    const moreButton = page.getByRole("button", { name: "more_vert" });
    await expect(moreButton).toBeVisible();
  });
});
