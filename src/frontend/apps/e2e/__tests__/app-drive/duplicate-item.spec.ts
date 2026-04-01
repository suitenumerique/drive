import test, { expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import {
  createFileFromTemplate,
  createFolderInCurrentFolder,
} from "./utils-item";
import { expectRowItem, getRowItem } from "./utils-embedded-grid";

/**
 * Sets up API route interceptions to control the duplicating state timing.
 * - Intercepts POST /items/{id}/duplicate/ to capture the duplicated item ID
 * - Intercepts GET /items/{id}/ (poll requests) to keep returning "duplicating"
 *   until releaseDuplicating() is called
 */
const setupDuplicateMocks = async (page: Page) => {
  let duplicatedItemId: string | null = null;
  let forcedUploadState: string = "duplicating";

  await page.route("**/api/v1.0/items/*/duplicate/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    duplicatedItemId = json.id;
    json.upload_state = "duplicating";
    await route.fulfill({ response, json });
  });

  await page.route(
    (url) => /\/api\/v1\.0\/items\/[^/]+\/$/.test(url.pathname),
    async (route) => {
      if (
        duplicatedItemId &&
        route.request().url().includes(duplicatedItemId) &&
        route.request().method() === "GET"
      ) {
        const response = await route.fetch();
        const json = await response.json();
        json.upload_state = forcedUploadState;
        await route.fulfill({ response, json });
      } else {
        await route.continue();
      }
    },
  );

  return {
    releaseDuplicating: () => {
      forcedUploadState = "ready";
    },
  };
};

const triggerDuplicate = async (page: Page, itemName: string) => {
  const row = await getRowItem(page, itemName);
  await row.click({ button: "right" });
  await page.getByRole("menuitem", { name: "Duplicate" }).click();
};

test.describe("Duplicate item", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
  });

  // --- Real e2e - Happy path ---

  test("Duplicates a file via context menu and the copy appears as ready", async ({
    page,
  }) => {
    await createFileFromTemplate(page, "TestDoc");

    const [response] = await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().includes("/duplicate/") && resp.status() === 201,
      ),
      triggerDuplicate(page, "TestDoc"),
    ]);

    const newItem = await response.json();
    const copyTitle = newItem.title;

    // The duplicated item should appear in the grid
    await expectRowItem(page, copyTitle);

    // It should eventually reach ready state (no spinner, no duplicating label)
    await expect(page.getByText("(duplication in progress)")).not.toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator("tr.duplicating")).not.toBeVisible();
  });

  test("Duplicate option is available for files but not folders", async ({
    page,
  }) => {
    await createFileFromTemplate(page, "TestDoc");
    await createFolderInCurrentFolder(page, "TestFolder");

    // File should have Duplicate option
    const fileRow = await getRowItem(page, "TestDoc");
    await fileRow.click({ button: "right" });
    await expect(
      page.getByRole("menuitem", { name: "Duplicate" }),
    ).toBeVisible();
    await page.keyboard.press("Escape");

    // Folder should NOT have Duplicate option
    const folderRow = await getRowItem(page, "TestFolder");
    await folderRow.click({ button: "right" });
    await expect(
      page.getByRole("menuitem", { name: "Duplicate" }),
    ).not.toBeVisible();
  });

  // --- Mocked API - Duplicating UI state ---

  test("Shows spinner and duplicating label while item is duplicating", async ({
    page,
  }) => {
    await createFileFromTemplate(page, "TestDoc");
    await setupDuplicateMocks(page);

    await triggerDuplicate(page, "TestDoc");

    const duplicatingRow = page.locator("tr.duplicating");
    await expect(duplicatingRow).toBeVisible({ timeout: 10000 });

    const nameCell = duplicatingRow.locator(".explorer__grid__item__name");
    await expect(nameCell.locator(".drive-loading-ring")).toBeVisible();
    await expect(nameCell.getByText("(duplication in progress)")).toBeVisible();
  });

  test("Hides action menu for duplicating item", async ({ page }) => {
    await createFileFromTemplate(page, "TestDoc");
    await setupDuplicateMocks(page);

    await triggerDuplicate(page, "TestDoc");

    const duplicatingRow = page.locator("tr.duplicating");
    await expect(duplicatingRow).toBeVisible({ timeout: 10000 });

    // The actions button should not be present in the duplicating row
    await expect(
      duplicatingRow.getByRole("button", { name: /More actions/ }),
    ).not.toBeVisible();
  });

  test("Duplicating row is not interactive", async ({ page }) => {
    await createFileFromTemplate(page, "TestDoc");
    await setupDuplicateMocks(page);

    await triggerDuplicate(page, "TestDoc");

    const duplicatingRow = page.locator("tr.duplicating");
    await expect(duplicatingRow).toBeVisible({ timeout: 10000 });
    // Click on the duplicating row should not navigate or open the file
    await duplicatingRow.click();
    await expect(duplicatingRow).toBeVisible();

    // Right-click should not open any context menu
    await duplicatingRow.click({ button: "right" });
    await expect(
      page.getByRole("menuitem", { name: "New folder" }),
    ).not.toBeVisible();
  });

  test("Transitions from duplicating to ready state after polling", async ({
    page,
  }) => {
    await createFileFromTemplate(page, "TestDoc");
    const { releaseDuplicating } = await setupDuplicateMocks(page);

    await triggerDuplicate(page, "TestDoc");

    // Verify duplicating state
    const duplicatingRow = page.locator("tr.duplicating");
    await expect(duplicatingRow).toBeVisible({ timeout: 10000 });

    const nameCell = duplicatingRow.locator(".explorer__grid__item__name");
    await expect(nameCell.locator(".drive-loading-ring")).toBeVisible();
    await expect(nameCell.getByText("(duplication in progress)")).toBeVisible();

    // Release the mock — next poll will return the real "ready" state
    releaseDuplicating();

    // Verify transition to ready (poll interval is 3s)
    // Check at page level since the tr.duplicating locator won't match once the class is removed
    await expect(duplicatingRow).not.toBeVisible({ timeout: 15000 });
    await expect(page.locator(".drive-loading-ring")).not.toBeVisible();
    await expect(page.getByText("(duplication in progress)")).not.toBeVisible();
  });

  test("Shows error toast when duplication fails", async ({ page }) => {
    await createFileFromTemplate(page, "TestDoc");

    // Mock the duplicate endpoint to return a 500 error
    await page.route("**/api/v1.0/items/*/duplicate/", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await triggerDuplicate(page, "TestDoc");

    // The error toast should appear
    await expect(
      page.getByText("An error occurred while duplicating the item."),
    ).toBeVisible({ timeout: 5000 });
  });

  test("Right-click context menu is disabled on duplicating row", async ({
    page,
  }) => {
    await createFileFromTemplate(page, "TestDoc");
    await setupDuplicateMocks(page);

    await triggerDuplicate(page, "TestDoc");

    const duplicatingRow = page.locator("tr.duplicating");
    await expect(duplicatingRow).toBeVisible({ timeout: 10000 });

    // Force right-click bypassing pointer-events: none
    await duplicatingRow.click({ button: "right", force: true });

    // No item context menu should appear
    await expect(
      page.getByRole("menuitem", { name: "Duplicate" }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Delete" }),
    ).not.toBeVisible();

    // No global context menu should appear either (new folder, etc.)
    await expect(
      page.getByRole("menuitem", { name: "New folder" }),
    ).not.toBeVisible();
  });
});
