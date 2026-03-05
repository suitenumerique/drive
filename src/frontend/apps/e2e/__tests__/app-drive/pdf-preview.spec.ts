import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { uploadFile } from "./utils/upload-utils";

const PDF_FILE_PATH = path.join(__dirname, "/assets/pv_cm.pdf");

import type { Page, Locator } from "@playwright/test";

/**
 * Dismiss the persistent upload toast overlay that blocks pointer events
 * on the PDF preview controls.
 */
async function dismissToast(page: Page) {
  const closeBtn = page.locator(".Toastify__toast").getByRole("button", {
    name: "close",
  });
  if ((await closeBtn.count()) > 0) {
    await closeBtn.first().dispatchEvent("click");
    await page
      .locator(".Toastify__toast")
      .first()
      .waitFor({ state: "detached", timeout: 5000 });
  }
}

async function waitForPdfReady(page: Page) {
  await expect(page.locator(".react-pdf__Page").first()).toBeVisible({
    timeout: 10000,
  });
}

async function openSidebar(page: Page) {
  const toggle = page.locator('button[aria-label="Toggle sidebar"]');
  await toggle.dispatchEvent("click");
  await expect(page.locator("[data-thumb-page]").first()).toBeVisible({
    timeout: 10000,
  });
}

async function expectActiveThumbnail(page: Page, pageNum: number) {
  await expect(
    page.locator(`[data-thumb-page="${pageNum}"]`),
  ).toHaveClass(/pdf-preview__thumbnail--active/, { timeout: 10000 });
}

async function expectInactiveThumbnail(page: Page, pageNum: number) {
  await expect(
    page.locator(`[data-thumb-page="${pageNum}"]`),
  ).not.toHaveClass(/pdf-preview__thumbnail--active/);
}

async function scrollPdfViewer(page: Page, deltaY: number) {
  const grid = page.locator(
    ".pdf-preview__container .ReactVirtualized__Grid",
  );
  await grid.hover();
  await page.mouse.wheel(0, deltaY);
}

function getPageInput(page: Page): Locator {
  return page.locator('input[aria-label="Current page"]');
}

test.describe("PDF Preview", () => {
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
    await expect(page.locator(".pdf-preview")).toBeVisible({ timeout: 10000 });
  });

  test("Opens the PDF viewer when double-clicking a PDF file", async ({
    page,
  }) => {
    await expect(page.getByTestId("file-preview")).toBeVisible();
    await expect(page.locator(".pdf-preview")).toBeVisible();

    await expect(
      page
        .locator(".textLayer")
        .getByText("PROCÈS VERBAL DU CONSEIL MUNICIPAL")
        .first(),
    ).toBeAttached({ timeout: 10000 });
  });

  test("Displays the correct page count in the controls bar", async ({
    page,
  }) => {
    const pageInput = getPageInput(page);
    await expect(pageInput).toBeVisible();
    await expect(pageInput).toHaveValue("1");

    const pageTotal = page.locator(".pdf-preview__page-total");
    await expect(pageTotal).toBeVisible();
    await expect(pageTotal).toHaveText("/ 9");
  });

  test("Shows the controls bar with all expected buttons", async ({ page }) => {
    const controls = page.locator(".pdf-preview__controls");
    await expect(controls).toBeVisible();

    await expect(
      controls.locator('button[aria-label="Toggle sidebar"]'),
    ).toBeVisible();

    const zoomButtons = controls.locator(".pdf-preview__zoom-controls button");
    await expect(zoomButtons).toHaveCount(3);
  });

  // Section 2 — Zoom controls

  test("Zooms in when clicking the zoom-in button", async ({ page }) => {
    const pdfPage = page.locator(".react-pdf__Page").first();
    await waitForPdfReady(page);

    const initialBox = await pdfPage.boundingBox();
    expect(initialBox).toBeTruthy();
    const initialWidth = initialBox!.width;

    const zoomIn = page.locator(
      ".pdf-preview__zoom-controls button >> nth=2",
    );
    await zoomIn.dispatchEvent("click");

    await expect(async () => {
      const box = await pdfPage.boundingBox();
      expect(box!.width).toBeGreaterThan(initialWidth);
    }).toPass({ timeout: 10000 });
  });

  test("Zooms out when clicking the zoom-out button", async ({ page }) => {
    const pdfPage = page.locator(".react-pdf__Page").first();
    await waitForPdfReady(page);

    const initialBox = await pdfPage.boundingBox();
    const initialWidth = initialBox!.width;

    const zoomIn = page.locator(
      ".pdf-preview__zoom-controls button >> nth=2",
    );
    const zoomOut = page.locator(
      ".pdf-preview__zoom-controls button >> nth=0",
    );

    await zoomIn.dispatchEvent("click");
    await expect(async () => {
      const box = await pdfPage.boundingBox();
      expect(box!.width).toBeGreaterThan(initialWidth);
    }).toPass({ timeout: 10000 });

    await zoomOut.dispatchEvent("click");
    await expect(async () => {
      const box = await pdfPage.boundingBox();
      expect(Math.round(box!.width)).toBe(Math.round(initialWidth));
    }).toPass({ timeout: 10000 });
  });

  test("Resets zoom to default when clicking the reset button", async ({
    page,
  }) => {
    const pdfPage = page.locator(".react-pdf__Page").first();
    await waitForPdfReady(page);

    const initialBox = await pdfPage.boundingBox();
    const initialWidth = initialBox!.width;

    const zoomIn = page.locator(
      ".pdf-preview__zoom-controls button >> nth=2",
    );
    const zoomReset = page.locator(
      ".pdf-preview__zoom-controls button >> nth=1",
    );

    await zoomIn.dispatchEvent("click");
    await zoomIn.dispatchEvent("click");
    await expect(async () => {
      const box = await pdfPage.boundingBox();
      expect(box!.width).toBeGreaterThan(initialWidth);
    }).toPass({ timeout: 10000 });

    await zoomReset.dispatchEvent("click");
    await expect(async () => {
      const box = await pdfPage.boundingBox();
      expect(Math.round(box!.width)).toBe(Math.round(initialWidth));
    }).toPass({ timeout: 10000 });
  });

  // Section 3 — Thumbnail sidebar

  test("Opens and closes the thumbnail sidebar", async ({ page }) => {
    await expect(page.locator(".pdf-preview__sidebar")).not.toBeAttached();

    await openSidebar(page);

    await expect(page.locator(".pdf-preview__sidebar")).toBeVisible();

    const toggle = page.locator('button[aria-label="Toggle sidebar"]');
    await toggle.dispatchEvent("click");

    await expect(page.locator(".pdf-preview__sidebar")).not.toBeAttached({
      timeout: 5000,
    });
  });

  test("Marks the current page thumbnail as active", async ({ page }) => {
    await openSidebar(page);

    await expectActiveThumbnail(page, 1);
    await expectInactiveThumbnail(page, 2);
  });

  test("Navigates to a page when clicking a thumbnail", async ({ page }) => {
    await openSidebar(page);

    await page.locator('button[aria-label="Go to page 3"]').dispatchEvent("click");

    const pageInput = getPageInput(page);
    await expect(pageInput).toHaveValue("3", { timeout: 5000 });
    await expectActiveThumbnail(page, 3);
  });

  test("Updates the active thumbnail when scrolling the document", async ({
    page,
  }) => {
    await openSidebar(page);
    await waitForPdfReady(page);
    await dismissToast(page);

    await expectActiveThumbnail(page, 1);

    await scrollPdfViewer(page, 3000);

    await expectActiveThumbnail(page, 3);
    await expectInactiveThumbnail(page, 1);
  });

  // Section 4 — Page navigation

  test("Navigates to a specific page via the page input", async ({ page }) => {
    const pageInput = getPageInput(page);
    await expect(pageInput).toBeVisible();
    await waitForPdfReady(page);
    await dismissToast(page);

    await pageInput.fill("5");
    await pageInput.press("Enter");

    await expect(pageInput).toHaveValue("5", { timeout: 5000 });
  });

  test("Clamps out-of-range page numbers to valid range", async ({ page }) => {
    const pageInput = getPageInput(page);
    await expect(pageInput).toBeVisible();
    await waitForPdfReady(page);
    await dismissToast(page);

    await pageInput.fill("99");
    await pageInput.press("Enter");

    await expect(pageInput).toHaveValue("9", { timeout: 5000 });
  });

  test("Resets invalid input to current page on blur", async ({ page }) => {
    const pageInput = getPageInput(page);
    await expect(pageInput).toHaveValue("1");
    await dismissToast(page);

    await pageInput.fill("abc");
    await pageInput.blur();

    await expect(pageInput).toHaveValue("1", { timeout: 5000 });
  });

  test("Updates page number when scrolling the document", async ({ page }) => {
    const pageInput = getPageInput(page);
    await expect(pageInput).toHaveValue("1");
    await waitForPdfReady(page);
    await dismissToast(page);

    await scrollPdfViewer(page, 3000);

    await expect(async () => {
      const value = await pageInput.inputValue();
      expect(value).not.toBe("1");
    }).toPass({ timeout: 10000 });
  });
});
