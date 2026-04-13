import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { uploadFile } from "./utils/upload-utils";

const PDF_FILE_PATH = path.join(__dirname, "/assets/pv_cm.pdf");
const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

test.describe("File Preview Actions Menu", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, PDF_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page.getByRole("cell", { name: "pv_cm", exact: true }).dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });
  });

  test("Shows the actions dropdown with download and print options", async ({
    page,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    const moreButton = filePreview.locator(
      ".file-preview__header__content__right button:has(.material-icons)",
    );

    // Find the "..." button (more_vert icon)
    const moreVertButton = filePreview.getByText("more_vert").locator("..");
    await expect(moreVertButton).toBeVisible();
    await moreVertButton.click();

    // Verify both menu items appear
    await expect(
      page.getByRole("menuitem", { name: "Download" }),
    ).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Print" })).toBeVisible();
  });

  test("Download action in dropdown triggers file download", async ({
    page,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    const moreVertButton = filePreview.getByText("more_vert").locator("..");
    await moreVertButton.click();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("menuitem", { name: "Download" }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toContain("pv_cm");
  });

  test("Updates the browser tab title when preview is open", async ({
    page,
  }) => {
    // The title should include the file name while preview is open
    await expect(page).toHaveTitle(/pv_cm\.pdf/);

    // Close the preview
    const filePreview = page.getByTestId("file-preview");
    const closeButton = filePreview.locator(
      ".file-preview__header__content__left button",
    );
    await closeButton.click();

    // The title should no longer contain the file name
    await expect(page).not.toHaveTitle(/pv_cm\.pdf/);
  });

  test("Print action in dropdown opens the file in a new tab", async ({
    page,
    context,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    const moreVertButton = filePreview.getByText("more_vert").locator("..");
    await moreVertButton.click();

    const [newPage] = await Promise.all([
      context.waitForEvent("page"),
      page.getByRole("menuitem", { name: "Print" }).click(),
    ]);

    // A new tab was opened with the file for printing
    expect(newPage).toBeTruthy();
    await newPage.close();
  });
});

test.describe("File Preview Actions Menu - Non-printable file", () => {
  test("Hides the actions menu for non-PDF/non-image files", async ({
    page,
  }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, DOCX_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page.getByRole("cell", { name: "empty_doc", exact: true }).dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });

    const filePreview = page.getByTestId("file-preview");
    await expect(
      filePreview.getByText("more_vert"),
    ).not.toBeVisible();
  });
});
