import test, { expect } from "@playwright/test";
import path from "path";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles, clickToRecent } from "./utils-navigate";
import {
  createFolderInCurrentFolder,
  createFileFromTemplate,
  importFile,
} from "./utils-item";
import {
  changeColumnType,
  clickColumnSortButton,
  clickNameSortButton,
  expectColumnHeaderLabel,
  expectRowNamesInOrder,
  getCellText,
  getColumnHeader,
} from "./utils/custom-columns-utils";

const PDF_FILE_PATH = path.join(__dirname, "/assets/pv_cm.pdf");
const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

test.describe("Custom columns", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
  });

  // ── Group 1: Default columns ──────────────────────────────────

  test("Default columns are Last modified and Created by", async ({
    page,
  }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    await expectColumnHeaderLabel(page, 1, "Last modified");
    await expectColumnHeaderLabel(page, 2, "Created by");

    // The Last modified cell should show a relative time
    const cellText = await getCellText(page, "TestFolder", 1);
    expect(cellText).toMatch(/seconds? ago|minute/);
  });

  // ── Group 2: Change column types ──────────────────────────────

  test("Change column 1 type via dropdown", async ({ page }) => {
    await importFile(page, PDF_FILE_PATH);
    // Wait for the uploaded file to appear (no optimistic update, needs API round-trip)
    const fileRow = page.getByRole("row").filter({ hasText: "pv_cm" }).first();
    await expect(fileRow).toBeVisible({ timeout: 15000 });

    await changeColumnType(page, 1, "File size");
    await expectColumnHeaderLabel(page, 1, "File size");

    // File should show a size value (not "-")
    const cellText = await getCellText(page, "pv_cm", 1);
    expect(cellText).not.toBe("-");
    expect(cellText).toBeTruthy();
  });

  test("Change column 2 type via dropdown", async ({ page }) => {
    await createFolderInCurrentFolder(page, "MyFolder");

    await changeColumnType(page, 2, "File type");
    await expectColumnHeaderLabel(page, 2, "File type");

    const cellText = await getCellText(page, "MyFolder", 2);
    expect(cellText).toBe("Folder");
  });

  test("Change both columns", async ({ page }) => {
    await createFolderInCurrentFolder(page, "MyFolder");

    await changeColumnType(page, 1, "Created");
    await changeColumnType(page, 2, "File size");

    await expectColumnHeaderLabel(page, 1, "Created");
    await expectColumnHeaderLabel(page, 2, "File size");

    // Folder has no file size
    const sizeText = await getCellText(page, "MyFolder", 2);
    expect(sizeText).toBe("-");

    // Created should show a relative time
    const createdText = await getCellText(page, "MyFolder", 1);
    expect(createdText).toMatch(/seconds? ago|minute/);
  });

  // ── Group 3: Persistence ──────────────────────────────────────

  test("Column preferences persist after page reload", async ({ page }) => {
    await createFolderInCurrentFolder(page, "MyFolder");

    await changeColumnType(page, 1, "File type");
    await expectColumnHeaderLabel(page, 1, "File type");

    await page.reload();
    await clickToMyFiles(page);

    await expectColumnHeaderLabel(page, 1, "File type");
  });

  test("Column preferences are shared across views", async ({ page }) => {
    // Create a file (not a folder) because Recents uses files_only mode
    await createFileFromTemplate(page, "TestDoc");

    await changeColumnType(page, 1, "File size");
    await expectColumnHeaderLabel(page, 1, "File size");

    await clickToRecent(page);
    // Wait for the file to appear in Recents
    const fileRow = page
      .getByRole("row")
      .filter({ hasText: "TestDoc" })
      .first();
    await expect(fileRow).toBeVisible({ timeout: 10000 });

    await expectColumnHeaderLabel(page, 1, "File size");
  });

  // ── Group 4: Sorting ──────────────────────────────────────────

  test("Sort by Name column cycles through asc/desc/default", async ({
    page,
  }) => {
    await createFolderInCurrentFolder(page, "AAA");
    await createFolderInCurrentFolder(page, "CCC");
    await createFolderInCurrentFolder(page, "BBB");

    // Default order: folders first, sorted by title = AAA, BBB, CCC
    await expectRowNamesInOrder(page, ["AAA", "BBB", "CCC"]);

    // Click sort → ascending
    await clickNameSortButton(page);
    await expectRowNamesInOrder(page, ["AAA", "BBB", "CCC"]);

    // Click sort → descending
    await clickNameSortButton(page);
    await expectRowNamesInOrder(page, ["CCC", "BBB", "AAA"]);

    // Click sort → reset to default
    await clickNameSortButton(page);
    await expectRowNamesInOrder(page, ["AAA", "BBB", "CCC"]);
  });

  test("Sort by a customizable column (Last modified)", async ({ page }) => {
    await createFolderInCurrentFolder(page, "First");
    // Delay to ensure distinct updated_at timestamps
    await page.waitForTimeout(2000);
    await createFolderInCurrentFolder(page, "Second");

    // Click sort on col1 (Last modified) → ascending (oldest first)
    await clickColumnSortButton(page, 1);
    await expectRowNamesInOrder(page, ["First", "Second"]);

    // Click again → descending (newest first)
    await clickColumnSortButton(page, 1);
    await expectRowNamesInOrder(page, ["Second", "First"]);
  });

  test("Sort by File size after changing column type", async ({ page }) => {
    // Import two files of different sizes to avoid folders_first interference
    await importFile(page, PDF_FILE_PATH);
    await page.getByRole("row").filter({ hasText: "pv_cm" }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });

    await importFile(page, DOCX_FILE_PATH);
    await page
      .getByRole("row")
      .filter({ hasText: "empty_doc" })
      .first()
      .waitFor({ state: "visible", timeout: 15000 });

    await changeColumnType(page, 1, "File size");
    await expectColumnHeaderLabel(page, 1, "File size");

    // Click sort on col1 → ascending (smallest first)
    await clickColumnSortButton(page, 1);
    await expectRowNamesInOrder(page, ["empty_doc", "pv_cm"]);

    // Click again → descending (largest first)
    await clickColumnSortButton(page, 1);
    await expectRowNamesInOrder(page, ["pv_cm", "empty_doc"]);
  });

  // ── Group 5: Cell content ─────────────────────────────────────

  test("Cells display correct content for each column type", async ({
    page,
  }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    // Switch col1 to File size → folders show "-"
    await changeColumnType(page, 1, "File size");
    const sizeText = await getCellText(page, "TestFolder", 1);
    expect(sizeText).toBe("-");

    // Switch col2 to File type → folders show "Folder"
    await changeColumnType(page, 2, "File type");
    const typeText = await getCellText(page, "TestFolder", 2);
    expect(typeText).toBe("Folder");

    // Switch col1 to Created → shows relative time
    await changeColumnType(page, 1, "Created");
    const createdText = await getCellText(page, "TestFolder", 1);
    expect(createdText).toMatch(/seconds? ago|minute/);
  });

  // ── Group 6: Default marker in dropdown ───────────────────────

  test("Default column option is marked in dropdown", async ({ page }) => {
    await createFolderInCurrentFolder(page, "TestFolder");

    // Open col1 dropdown — default for col1 is "Last modified"
    const header1 = getColumnHeader(page, 1);
    const dropdownButton1 = header1
      .locator(".explorer__grid__header button")
      .first();
    await dropdownButton1.click();

    await expect(
      page.getByRole("menuitem", { name: "Last modified (default)" }),
    ).toBeVisible();

    // Close dropdown
    await page.keyboard.press("Escape");

    // Open col2 dropdown — default for col2 is "Created by"
    const header2 = getColumnHeader(page, 2);
    const dropdownButton2 = header2
      .locator(".explorer__grid__header button")
      .first();
    await dropdownButton2.click();

    await expect(
      page.getByRole("menuitem", { name: "Created by (default)" }),
    ).toBeVisible();
  });
});
