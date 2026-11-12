import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";

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

    const moreButton = page.getByRole("button", { name: "More actions" });
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

    // Wait until the folder is open. Reading the URL right after dblclick
    // still points at the parent listing, whose row action shares this name
    // with the dnd-kit draggable wrapped around it.
    await navigateToFolder(page, "TestFolder", ["My files", "TestFolder"]);
    const folderUrl = page.url();

    await page.setViewportSize(MOBILE_VIEWPORT);
    await page.goto(folderUrl);

    const moreButton = page
      .locator(".explorer__content__breadcrumbs--mobile")
      .getByRole("button", { name: "More actions for TestFolder" });
    await expect(moreButton).toBeVisible();
  });
});
