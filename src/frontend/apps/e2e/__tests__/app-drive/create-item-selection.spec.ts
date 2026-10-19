import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { getRowItem } from "./utils-embedded-grid";
import {
  createFileFromTemplate,
  createFolderInCurrentFolder,
} from "./utils-item";
import { navigateToFolder } from "./utils-navigate";

test.describe("Select created item", () => {
  test.beforeEach(async ({ page }) => {
    // 1. Start from an empty "My files".
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
  });

  test("A created folder is selected", async ({ page }) => {
    // 2. Create a folder from the "New" menu.
    await createFolderInCurrentFolder(page, "My folder");

    // 3. The new folder is selected so the user can spot it in the list.
    await expect(await getRowItem(page, "My folder")).toHaveClass(/selected/);
    await expect(page.getByText("1 item selected")).toBeVisible();
  });

  test("A created document is selected", async ({ page }) => {
    // 2. Create a document inside a folder, so it is not the only item of
    //    "My files" and the selection matters.
    await createFolderInCurrentFolder(page, "Test folder");
    await navigateToFolder(page, "Test folder", ["My files", "Test folder"]);
    await createFileFromTemplate(page, "My document");

    // 3. The new document is selected, replacing any previous selection.
    await expect(await getRowItem(page, "My document")).toHaveClass(/selected/);
    await expect(page.getByText("1 item selected")).toBeVisible();
  });
});
