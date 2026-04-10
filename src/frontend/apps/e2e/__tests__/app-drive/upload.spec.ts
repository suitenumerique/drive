import test, { expect } from "@playwright/test";
import { clearDb } from "./utils-common";
import path from "path";
import {
  uploadFile,
  setupUploadTest,
  getUploadToast,
  getFileRow,
  getFileRowErrorText,
  getFileRowCheckIcon,
  getToastDescriptionText,
  getToastErrorIndicator,
  getToastToggleButton,
  getToastCloseButton,
  getFilesList,
  mockSlowUpload,
  mockSlowUploadEnded,
} from "./utils/upload-utils";
import { createFolderInCurrentFolder, deleteCurrentFolder } from "./utils-item";
import { navigateToFolder, clickToMyFiles } from "./utils-navigate";
import { clickOnRowItemActions } from "./utils-embedded-grid";

const PDF_FILE_PATH = path.join(__dirname, "/assets/pv_cm.pdf");
const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

test.describe("File upload toast", () => {
  test.beforeEach(async () => {
    await clearDb();
  });

  test("Upload successful — progress and success", async ({ page }) => {
    await setupUploadTest(page);

    await uploadFile(page, PDF_FILE_PATH);

    // Toast should be visible
    await expect(getUploadToast(page)).toBeVisible();

    // Wait for the file to appear in the grid
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    // Toast should show success
    await expect(getToastDescriptionText(page)).toContainText(
      "1 file transferred",
    );
    await expect(getFileRowCheckIcon(page, "pv_cm.pdf")).toBeVisible();
  });

  test("File too large — error in toast", async ({ page }) => {
    await setupUploadTest(page, 1024); // 1 KB

    await uploadFile(page, PDF_FILE_PATH);

    // Toast visible with the file row showing error
    await expect(getUploadToast(page)).toBeVisible();
    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();
    await expect(getFileRowErrorText(page, "pv_cm.pdf")).toContainText(
      "File too large",
    );

    // Error icon should be visible on the row
    await expect(
      getFileRow(page, "pv_cm.pdf").locator(
        ".file-upload-toast__files__item__error-icon",
      ),
    ).toBeVisible();

    // File must NOT appear in the grid
    await expect(page.getByText("This tab is empty")).toBeVisible();
  });

  test("Mix of normal and too-large files", async ({ page }) => {
    // 100 KB: empty_doc.docx (~7KB) passes, pv_cm.pdf (~253KB) rejected
    await setupUploadTest(page, 100 * 1024);

    await uploadFile(page, [DOCX_FILE_PATH, PDF_FILE_PATH]);

    // empty_doc.docx should succeed
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true }),
    ).toBeVisible({ timeout: 15000 });
    await expect(
      getFileRowCheckIcon(page, "empty_doc.docx"),
    ).toBeVisible();

    // pv_cm.pdf should be in error
    await expect(getFileRowErrorText(page, "pv_cm.pdf")).toContainText(
      "File too large",
    );

    // Only empty_doc.docx in the grid, not pv_cm.pdf
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).not.toBeVisible();
  });

  test("Error details on file row", async ({ page }) => {
    await setupUploadTest(page, 1024);

    await uploadFile(page, PDF_FILE_PATH);

    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();

    // The error text and icon should be visible on the row
    await expect(getFileRowErrorText(page, "pv_cm.pdf")).toContainText(
      "File too large",
    );
    await expect(
      getFileRow(page, "pv_cm.pdf").locator(
        ".file-upload-toast__files__item__error-icon",
      ),
    ).toBeVisible();
  });

  test("Error indicator in toast description", async ({ page }) => {
    await setupUploadTest(page, 1024);

    await uploadFile(page, PDF_FILE_PATH);

    // ErrorIcon should be visible in the description bar
    await expect(getToastErrorIndicator(page)).toBeVisible();

    // Description text should also be visible next to the error icon
    await expect(getToastDescriptionText(page)).toBeVisible();
    await expect(getToastDescriptionText(page)).not.toBeEmpty();
  });

  test("Toast stays open when there are errors", async ({ page }) => {
    await setupUploadTest(page, 1024);

    await uploadFile(page, PDF_FILE_PATH);

    // The files list should be visible (not collapsed)
    await expect(getFilesList(page)).toBeVisible();
    await expect(getFilesList(page)).not.toHaveClass(
      /file-upload-toast__files--closed/,
    );

    // The error file is shown
    await expect(getFileRowErrorText(page, "pv_cm.pdf")).toContainText(
      "File too large",
    );
  });

  test("Close toast after successful upload", async ({ page }) => {
    await setupUploadTest(page);

    await uploadFile(page, PDF_FILE_PATH);

    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    // Click close button
    await getToastCloseButton(page).click();

    // Toast should disappear
    await expect(getUploadToast(page)).not.toBeVisible();
  });

  test("Toggle open/close the file list", async ({ page }) => {
    await setupUploadTest(page);

    await uploadFile(page, PDF_FILE_PATH);

    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    // After success with 0 errors, list auto-closes
    await expect(getFilesList(page)).toHaveClass(
      /file-upload-toast__files--closed/,
    );

    // Click toggle → list opens
    await getToastToggleButton(page).click();
    await expect(getFilesList(page)).not.toHaveClass(
      /file-upload-toast__files--closed/,
    );

    // Click toggle again → list closes
    await getToastToggleButton(page).click();
    await expect(getFilesList(page)).toHaveClass(
      /file-upload-toast__files--closed/,
    );
  });

  test("Hover on uploading file — cancel overlay visible", async ({
    page,
  }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    await uploadFile(page, PDF_FILE_PATH);

    // File should be uploading with circular progress
    await expect(getUploadToast(page)).toBeVisible();
    const progressArea = getFileRow(page, "pv_cm.pdf").locator(
      ".file-upload-toast__files__item__progress--hoverable",
    );
    await expect(progressArea).toBeVisible();

    // Hover → cancel overlay appears
    await progressArea.hover();
    await expect(
      getFileRow(page, "pv_cm.pdf").locator(
        ".file-upload-toast__files__item__cancel-overlay",
      ),
    ).toBeVisible();

    // Mouse leave → cancel overlay disappears
    await page.mouse.move(0, 0);
    await expect(
      getFileRow(page, "pv_cm.pdf").locator(
        ".file-upload-toast__files__item__cancel-overlay",
      ),
    ).not.toBeVisible();

    // Clean up: resolve the upload to avoid hanging
    resolve();
  });

  test("Cancel individual file upload", async ({ page }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    await uploadFile(page, PDF_FILE_PATH);

    await expect(getUploadToast(page)).toBeVisible();
    const progressArea = getFileRow(page, "pv_cm.pdf").locator(
      ".file-upload-toast__files__item__progress--hoverable",
    );
    await expect(progressArea).toBeVisible();

    // Hover + click cancel overlay
    await progressArea.hover();
    await progressArea.click();

    // File row should disappear (status becomes cancelled → returns null)
    await expect(getFileRow(page, "pv_cm.pdf")).not.toBeVisible();

    resolve();
  });

  test("Cancel all via confirmation modal", async ({ page }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    await uploadFile(page, PDF_FILE_PATH);

    await expect(getUploadToast(page)).toBeVisible();

    // Click close button while uploading → modal opens
    await getToastCloseButton(page).click();

    // Verify modal content
    await expect(page.getByText("Leave upload?")).toBeVisible();
    await expect(
      page.getByText("Unfinished files will be lost."),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Keep uploading" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Leave and cancel" }),
    ).toBeVisible();

    // Click "Keep uploading" → modal closes, upload continues
    await page.getByRole("button", { name: "Keep uploading" }).click();
    await expect(page.getByText("Leave upload?")).not.toBeVisible();
    await expect(getUploadToast(page)).toBeVisible();

    // Click close again → modal opens again
    await getToastCloseButton(page).click();
    await expect(page.getByText("Leave upload?")).toBeVisible();

    // Click "Leave and cancel" → toast disappears
    await page.getByRole("button", { name: "Leave and cancel" }).click();
    await expect(getUploadToast(page)).not.toBeVisible();

    resolve();
  });

  test("Cancel all stops queued files too", async ({ page }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    // Upload 2 files — first one blocks, second is queued
    await uploadFile(page, [PDF_FILE_PATH, DOCX_FILE_PATH]);

    await expect(getUploadToast(page)).toBeVisible();
    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();
    await expect(getFileRow(page, "empty_doc.docx")).toBeVisible();

    // Cancel all via modal
    await getToastCloseButton(page).click();
    await expect(page.getByText("Leave upload?")).toBeVisible();
    await page.getByRole("button", { name: "Leave and cancel" }).click();

    // Toast should disappear — both files cancelled (including queued one)
    await expect(getUploadToast(page)).not.toBeVisible();

    resolve();

    // Neither file should appear in the grid
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true }),
    ).not.toBeVisible();
  });

  test("Cancel individual file during upload-ended phase", async ({
    page,
  }) => {
    const { resolve } = await mockSlowUploadEnded(page);
    await setupUploadTest(page);

    await uploadFile(page, PDF_FILE_PATH);

    // The S3 upload completes normally, progress reaches ~90%
    // then blocks on upload-ended — file should still show as uploading
    await expect(getUploadToast(page)).toBeVisible();
    const progressArea = getFileRow(page, "pv_cm.pdf").locator(
      ".file-upload-toast__files__item__progress--hoverable",
    );
    await expect(progressArea).toBeVisible();

    // Hover + click cancel overlay during upload-ended phase
    await progressArea.hover();
    await progressArea.click();

    // File row should disappear (cancelled)
    await expect(getFileRow(page, "pv_cm.pdf")).not.toBeVisible();

    resolve();

    // File should not appear in the grid
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).not.toBeVisible();
  });

  test("New drop during upload — files merge into toast", async ({
    page,
  }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    // Start first upload (blocked by mock)
    await uploadFile(page, PDF_FILE_PATH);
    await expect(getUploadToast(page)).toBeVisible();
    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();

    // Drop a second file while first is still uploading
    await uploadFile(page, DOCX_FILE_PATH);

    // Both files should appear in the toast
    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();
    await expect(getFileRow(page, "empty_doc.docx")).toBeVisible();

    // Unblock uploads
    resolve();

    // Both files should complete successfully
    await expect(getFileRowCheckIcon(page, "pv_cm.pdf")).toBeVisible({
      timeout: 15000,
    });
    await expect(getFileRowCheckIcon(page, "empty_doc.docx")).toBeVisible({
      timeout: 15000,
    });

    // Both files should appear in the grid
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true }),
    ).toBeVisible();
  });

  test("Toast stays visible after successful upload with no errors", async ({
    page,
  }) => {
    await setupUploadTest(page);

    await uploadFile(page, DOCX_FILE_PATH);

    // Wait for upload to complete
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    // Toast should still be visible with the success description
    await expect(getUploadToast(page)).toBeVisible();
    await expect(getToastDescriptionText(page)).toBeVisible();
    await expect(getToastDescriptionText(page)).toContainText(
      "1 file transferred",
    );
  });

  test("New upload after completed batch resets the file list", async ({
    page,
  }) => {
    await setupUploadTest(page);

    // First batch: upload pv_cm.pdf and wait for completion
    await uploadFile(page, PDF_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 15000 });
    await expect(getFileRowCheckIcon(page, "pv_cm.pdf")).toBeVisible();

    // Second batch: upload empty_doc.docx
    await uploadFile(page, DOCX_FILE_PATH);

    // Old file should be gone from the toast list
    await expect(getFileRow(page, "pv_cm.pdf")).not.toBeVisible();

    // New file should appear in the toast
    await expect(getFileRow(page, "empty_doc.docx")).toBeVisible();

    // Wait for second upload to complete
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true }),
    ).toBeVisible({ timeout: 15000 });
    await expect(getFileRowCheckIcon(page, "empty_doc.docx")).toBeVisible();
  });

  test("Delete parent folder — cancels active uploads", async ({ page }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    // Create a folder and navigate into it
    await createFolderInCurrentFolder(page, "TestFolder");
    await navigateToFolder(page, "TestFolder", ["My files", "TestFolder"]);

    // Start uploading a file (parentId = TestFolder.id)
    await uploadFile(page, PDF_FILE_PATH);

    // Toast should be visible with the file uploading
    await expect(getUploadToast(page)).toBeVisible();
    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();

    // Delete the current folder via breadcrumb — triggers cancelUploadsForDeletedItems
    await deleteCurrentFolder(page);

    // Upload should be cancelled — file row should disappear from toast
    await expect(getFileRow(page, "pv_cm.pdf")).not.toBeVisible();

    // Unblock the S3 mock
    resolve();

    // File should NOT appear in the grid (we're now back in My Files)
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).not.toBeVisible();
  });

  test("Delete folder only cancels uploads for that folder", async ({
    page,
  }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    // Create two folders
    await createFolderInCurrentFolder(page, "FolderA");
    await createFolderInCurrentFolder(page, "FolderB");

    // Navigate into FolderA and start uploading (blocked by mock)
    await navigateToFolder(page, "FolderA", ["My files", "FolderA"]);
    await uploadFile(page, PDF_FILE_PATH);
    await expect(getUploadToast(page)).toBeVisible();
    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();

    // Navigate back to My Files, then into FolderB
    await clickToMyFiles(page);
    await navigateToFolder(page, "FolderB", ["My files", "FolderB"]);

    // Start another upload (merged into queue)
    await uploadFile(page, DOCX_FILE_PATH);
    await expect(getFileRow(page, "empty_doc.docx")).toBeVisible();

    // Navigate back to My Files
    await clickToMyFiles(page);

    // Delete FolderA via row action menu — should only cancel FolderA's upload
    await clickOnRowItemActions(page, "FolderA", "Delete");

    // pv_cm.pdf (FolderA) should be cancelled
    await expect(getFileRow(page, "pv_cm.pdf")).not.toBeVisible();

    // empty_doc.docx (FolderB) should still be in the toast
    await expect(getFileRow(page, "empty_doc.docx")).toBeVisible();

    // Unblock uploads — FolderB's file should complete
    resolve();
    await expect(getFileRowCheckIcon(page, "empty_doc.docx")).toBeVisible({
      timeout: 15000,
    });
  });

  test("Delete ancestor folder — cancels uploads in a nested drop target", async ({
    page,
  }) => {
    const { resolve } = await mockSlowUpload(page);
    await setupUploadTest(page);

    // Create FolderA, go in, create FolderB inside, go in, start upload
    await createFolderInCurrentFolder(page, "FolderA");
    await navigateToFolder(page, "FolderA", ["My files", "FolderA"]);
    await createFolderInCurrentFolder(page, "FolderB");
    await navigateToFolder(page, "FolderB", ["My files", "FolderA", "FolderB"]);

    await uploadFile(page, PDF_FILE_PATH);
    await expect(getUploadToast(page)).toBeVisible();
    await expect(getFileRow(page, "pv_cm.pdf")).toBeVisible();

    // Go back up to My Files and delete FolderA (ancestor of the drop target)
    await clickToMyFiles(page);
    await clickOnRowItemActions(page, "FolderA", "Delete");

    // Upload should be cancelled via ancestor resolution
    await expect(getFileRow(page, "pv_cm.pdf")).not.toBeVisible();

    resolve();
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).not.toBeVisible();
  });
});
