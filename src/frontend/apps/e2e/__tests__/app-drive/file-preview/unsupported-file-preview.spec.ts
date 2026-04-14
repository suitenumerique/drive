import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "../utils-common";
import { clickToMyFiles } from "../utils-navigate";
import { uploadFile } from "../utils/upload-utils";

const UNSUPPORTED_FILE_PATH = path.join(
  __dirname,
  "../assets/test-unsupported.bin",
);

test.describe("Unsupported File Preview", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, UNSUPPORTED_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "test-unsupported.bin", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "test-unsupported.bin", exact: true })
      .dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });
  });

  test("Renders the NotSupportedPreview for an unknown binary file", async ({
    page,
  }) => {
    const unsupported = page.locator(".file-preview-unsupported");
    await expect(unsupported).toBeVisible();

    await expect(
      unsupported.locator(".file-preview-unsupported__title"),
    ).toHaveText("test-unsupported.bin");
  });

  test("Download button in the unsupported view triggers a download", async ({
    page,
  }) => {
    const downloadButton = page.locator(
      ".file-preview-unsupported__download-button",
    );
    await expect(downloadButton).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await downloadButton.click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toContain("test-unsupported");
  });

  test("Hides the actions menu for unsupported files", async ({ page }) => {
    const filePreview = page.getByTestId("file-preview");
    await expect(filePreview.getByText("more_vert")).not.toBeVisible();
  });
});
