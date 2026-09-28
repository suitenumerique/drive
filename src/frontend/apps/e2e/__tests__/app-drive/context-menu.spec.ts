import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import {
  createFileFromTemplate,
  createFolderInCurrentFolder,
} from "./utils-item";
import {
  expectRowItem,
  expectRowItemIsNotVisible,
  getRowItem,
} from "./utils-embedded-grid";
import { verifyItemIsStarred } from "./utils/starred-utils";
import { expectShareModal } from "./utils/share-utils";
import { expectMoveFolderModal } from "./utils/move-utils";

test.describe("Context menu", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
  });

  // --- Background right-click ---

  test("Right-click on empty area shows create menu items", async ({
    page,
  }) => {
    await createFolderInCurrentFolder(page, "Placeholder");

    const explorerContent = page.locator(".explorer__content");
    await explorerContent.click({ button: "right" });

    await expect(
      page.getByRole("menuitem", { name: "New folder" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "New text document" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "New slides" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "New spreadsheet" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Import files" }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Import folders" }),
    ).toBeVisible();
  });

  test("Right-click on empty area > Create folder works", async ({ page }) => {
    await createFolderInCurrentFolder(page, "Placeholder");

    const explorerContent = page.locator(".explorer__content");
    await explorerContent.click({ button: "right" });

    await page.getByRole("menuitem", { name: "New folder" }).click();

    await page.getByTestId("create-folder-input").fill("ContextMenuFolder");
    await page.getByRole("button", { name: "Create" }).click();

    await expectRowItem(page, "ContextMenuFolder");
  });

  // --- Item right-click ---

  test("Right-click on item shows action menu items", async ({ page }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    const row = await getRowItem(page, "TestFolder");
    await row.click({ button: "right" });

    await expect(
      page.getByRole("menuitem", { name: "Information" }),
    ).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Share" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Move" })).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Download" }),
    ).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Rename" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Star" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Delete" })).toBeVisible();
  });

  test("Right-click on folder > Download calls the export endpoint", async ({
    page,
  }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    await page.route("**/api/v1.0/items/*/export/", async (route) => {
      await route.fulfill({
        status: 200,
        headers: {
          "content-disposition": "attachment; filename=test.zip",
          "content-type": "application/zip",
        },
        body: "",
      });
    });

    const exportRequestPromise = page.waitForRequest((request) =>
      /\/api\/v1\.0\/items\/[^/]+\/export\/$/.test(request.url()),
    );

    const row = await getRowItem(page, "TestFolder");
    await row.click({ button: "right" });
    await page.getByRole("menuitem", { name: "Download" }).click();

    const exportRequest = await exportRequestPromise;
    expect(exportRequest.url()).toMatch(
      /\/api\/v1\.0\/items\/[^/]+\/export\/$/,
    );
  });

  test("Right-click on item > Rename works", async ({ page }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    const row = await getRowItem(page, "TestFolder");
    await row.click({ button: "right" });
    await page.getByRole("menuitem", { name: "Rename" }).click();

    await page.getByRole("textbox", { name: "New name" }).fill("RenamedFolder");
    await page.getByRole("button", { name: "Rename" }).click();

    await expectRowItem(page, "RenamedFolder");
    await expectRowItemIsNotVisible(page, "TestFolder");
  });

  test("Right-click on item > Delete works", async ({ page }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    const row = await getRowItem(page, "TestFolder");
    await row.click({ button: "right" });
    await page.getByRole("menuitem", { name: "Delete" }).click();

    await expectRowItemIsNotVisible(page, "TestFolder");
  });

  test("Right-click on item > Star works", async ({ page }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    const row = await getRowItem(page, "TestFolder");
    await row.click({ button: "right" });
    await page.getByRole("menuitem", { name: "Star" }).click();

    await verifyItemIsStarred(page, "TestFolder");
  });

  // --- File item right-click ---

  test("Right-click on file shows action menu items including Download", async ({
    page,
  }) => {
    await createFileFromTemplate(page, "TestDoc");

    const row = await getRowItem(page, "TestDoc");
    await row.click({ button: "right" });

    await expect(
      page.getByRole("menuitem", { name: "Information" }),
    ).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Share" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Move" })).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Download" }),
    ).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Rename" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Star" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Delete" })).toBeVisible();
  });

  test("Right-click on file > Share opens modal", async ({ page }) => {
    await createFileFromTemplate(page, "TestDoc");

    const row = await getRowItem(page, "TestDoc");
    await row.click({ button: "right" });
    await page.getByRole("menuitem", { name: "Share" }).click();

    await expectShareModal(page);
  });

  test("Right-click on file > Move opens modal", async ({ page }) => {
    await createFileFromTemplate(page, "TestDoc");

    const row = await getRowItem(page, "TestDoc");
    await row.click({ button: "right" });
    await page.getByRole("menuitem", { name: "Move" }).click();

    await expectMoveFolderModal(page);
  });
});
