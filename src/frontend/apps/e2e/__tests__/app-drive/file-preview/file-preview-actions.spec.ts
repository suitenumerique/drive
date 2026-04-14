import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "../utils-common";
import { clickToMyFiles } from "../utils-navigate";
import { uploadFile } from "../utils/upload-utils";

const PDF_FILE_PATH = path.join(__dirname, "../assets/pv_cm.pdf");
const DOCX_FILE_PATH = path.join(__dirname, "../assets/empty_doc.docx");

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

test.describe("File Preview Header", () => {
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

  test("Closes the preview when the close button is clicked", async ({
    page,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    await expect(filePreview).toBeVisible();

    const closeButton = filePreview.locator(
      ".file-preview__header__content__left button",
    );
    await closeButton.click();

    await expect(page.getByTestId("file-preview")).not.toBeAttached({
      timeout: 5000,
    });
  });

  test("Toggles the info sidebar on and off", async ({ page }) => {
    const container = page.locator(".file-preview__container");
    const sidebar = page.locator(".file-preview-sidebar");

    await expect(container).not.toHaveClass(
      /file-preview__container--sidebar-open/,
    );
    await expect(sidebar).not.toHaveClass(/(^|\s)open(\s|$)/);

    const filePreview = page.getByTestId("file-preview");
    const infoButton = filePreview.getByText("info_outline").locator("..");
    await infoButton.click();

    await expect(container).toHaveClass(
      /file-preview__container--sidebar-open/,
      { timeout: 5000 },
    );
    await expect(sidebar).toHaveClass(/(^|\s)open(\s|$)/);

    await infoButton.click();

    await expect(container).not.toHaveClass(
      /file-preview__container--sidebar-open/,
      { timeout: 5000 },
    );
    await expect(sidebar).not.toHaveClass(/(^|\s)open(\s|$)/);
  });
});

test.describe("File Preview Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, PDF_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await uploadFile(page, DOCX_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page.getByRole("cell", { name: "pv_cm", exact: true }).dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });
  });

  test("Navigates between files with the prev/next buttons", async ({
    page,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    const title = filePreview.locator("h1.file-preview__title");
    const nextButton = page.locator(".file-preview__next-button button");
    const prevButton = page.locator(".file-preview__previous-button button");

    await expect(title).toHaveText("pv_cm");

    // With 2 files and pv_cm at a boundary, exactly one of prev/next is disabled.
    const nextDisabled = await nextButton.isDisabled();
    const prevDisabled = await prevButton.isDisabled();
    expect(nextDisabled).not.toBe(prevDisabled);

    // Click whichever is enabled — we should land on empty_doc.
    if (!nextDisabled) {
      await nextButton.click();
    } else {
      await prevButton.click();
    }
    await expect(title).toHaveText("empty_doc");

    // Boundary flipped: previously enabled is now disabled, vice versa.
    if (!nextDisabled) {
      await expect(nextButton).toBeDisabled();
      await expect(prevButton).toBeEnabled();
    } else {
      await expect(prevButton).toBeDisabled();
      await expect(nextButton).toBeEnabled();
    }
  });

  test("Navigates between files with ArrowLeft/ArrowRight keys", async ({
    page,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    const title = filePreview.locator("h1.file-preview__title");
    const nextButton = page.locator(".file-preview__next-button button");

    await expect(title).toHaveText("pv_cm");

    const nextDisabled = await nextButton.isDisabled();
    const forwardKey = nextDisabled ? "ArrowLeft" : "ArrowRight";
    const backwardKey = nextDisabled ? "ArrowRight" : "ArrowLeft";

    await page.keyboard.press(forwardKey);
    await expect(title).toHaveText("empty_doc");

    await page.keyboard.press(backwardKey);
    await expect(title).toHaveText("pv_cm");
  });

  test("Does not navigate files when arrow keys are pressed inside the PDF page input", async ({
    page,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    const title = filePreview.locator("h1.file-preview__title");

    await expect(title).toHaveText("pv_cm");

    const pageInput = page.locator('input[aria-label="Current page"]');
    await expect(pageInput).toBeVisible({ timeout: 10000 });
    await pageInput.focus();

    await page.keyboard.press("ArrowRight");
    await expect(title).toHaveText("pv_cm");

    await page.keyboard.press("ArrowLeft");
    await expect(title).toHaveText("pv_cm");
  });
});
