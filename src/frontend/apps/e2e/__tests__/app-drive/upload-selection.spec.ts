import test, { expect } from "@playwright/test";
import path from "path";
import { clearDb } from "./utils-common";
import {
  uploadFile,
  setupUploadTest,
  getToastDescriptionText,
  mockSlowUploadEnded,
} from "./utils/upload-utils";
import { getRowItem } from "./utils-embedded-grid";
import { createFolderInCurrentFolder } from "./utils-item";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";

const PDF_FILE_PATH = path.join(__dirname, "/assets/pv_cm.pdf");
const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

test.describe("Select uploaded file", () => {
  test.beforeEach(async () => {
    await clearDb();
  });

  test("A single uploaded file is selected once uploaded", async ({ page }) => {
    // 1. Log in and open an empty "My files".
    await setupUploadTest(page);

    // 2. Upload a single file.
    await uploadFile(page, PDF_FILE_PATH);
    await expect(getToastDescriptionText(page)).toContainText(
      "1 file transferred",
      { timeout: 15000 },
    );

    // 3. The uploaded file is selected so the user can spot it in the folder.
    const row = await getRowItem(page, "pv_cm");
    await expect(row).toHaveClass(/selected/);
    await expect(page.getByText("1 item selected")).toBeVisible();
  });

  test("Nothing is selected when several files are uploaded", async ({
    page,
  }) => {
    // 1. Log in and open an empty "My files".
    await setupUploadTest(page);

    // 2. Upload two files at once.
    await uploadFile(page, [PDF_FILE_PATH, DOCX_FILE_PATH]);
    await expect(getToastDescriptionText(page)).toContainText(
      "2 files transferred",
      { timeout: 15000 },
    );

    // 3. Both files are listed, but the selection is left untouched: the
    //    feature only targets single file uploads.
    await expect(await getRowItem(page, "pv_cm")).not.toHaveClass(/selected/);
    await expect(await getRowItem(page, "empty_doc")).not.toHaveClass(
      /selected/,
    );
    await expect(page.getByText(/items? selected/)).not.toBeVisible();
  });

  test("Nothing is selected when the user left the folder during the upload", async ({
    page,
  }) => {
    // 1. Block upload-ended so the upload is still running while we navigate.
    const { resolve } = await mockSlowUploadEnded(page);
    await setupUploadTest(page);
    await createFolderInCurrentFolder(page, "Other folder");

    // 2. Upload a single file in "My files", then move to another folder
    //    before the upload completes.
    await uploadFile(page, PDF_FILE_PATH);
    await navigateToFolder(page, "Other folder", ["My files", "Other folder"]);

    // 3. Let the upload finish: the file is not in the displayed folder, so
    //    selecting it would show a selection bar for an invisible item.
    resolve();
    await expect(getToastDescriptionText(page)).toContainText(
      "1 file transferred",
      { timeout: 15000 },
    );
    await expect(page.getByText(/items? selected/)).not.toBeVisible();

    // 4. Back in "My files", the file is there but not selected.
    await clickToMyFiles(page);
    await expect(await getRowItem(page, "pv_cm")).not.toHaveClass(/selected/);
  });
});
