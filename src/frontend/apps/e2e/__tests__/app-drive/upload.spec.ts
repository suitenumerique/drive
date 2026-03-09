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
} from "./utils/upload-utils";

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
});
