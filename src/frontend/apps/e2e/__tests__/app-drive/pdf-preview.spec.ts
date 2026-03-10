import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { uploadFile } from "./utils/upload-utils";

const PDF_FILE_PATH = path.join(__dirname, "/assets/pv_cm.pdf");
const PDF_LINKS_FILE_PATH = path.join(__dirname, "/assets/pdf_with_links.pdf");
const PDF_JS_FILE_PATH = path.join(__dirname, "/assets/pdf_with_js.pdf");
const PDF_JS_LINK_FILE_PATH = path.join(
  __dirname,
  "/assets/pdf_with_js_link.pdf",
);
const PDF_CORRUPTED_FILE_PATH = path.join(
  __dirname,
  "/assets/pdf_corrupted.pdf",
);

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
  await grid.evaluate((el, dy) => {
    el.scrollTop += dy;
  }, deltaY);
  // Let react-virtualized process the scroll event
  await page.waitForTimeout(500);
}

function getPageInput(page: Page): Locator {
  return page.locator('input[aria-label="Current page"]');
}

function getExternalLink(page: Page): Locator {
  return page
    .locator(
      ".annotationLayer section.linkAnnotation:not([data-internal-link]) a",
    )
    .first();
}

function getInternalLink(page: Page): Locator {
  return page.locator("[data-internal-link] a").first();
}

function getDisclaimerModal(page: Page): Locator {
  return page.getByRole("dialog", { name: "External link" });
}

async function clickExternalLinkAndWaitForModal(page: Page) {
  await getExternalLink(page).click({ force: true });
  const modal = getDisclaimerModal(page);
  await expect(modal).toBeVisible({ timeout: 5000 });
  return modal;
}

async function waitForPdfReadyAndDismissToast(page: Page) {
  await waitForPdfReady(page);
  await dismissToast(page);
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
    await waitForPdfReadyAndDismissToast(page);

    await expectActiveThumbnail(page, 1);

    await scrollPdfViewer(page, 3000);

    await expectActiveThumbnail(page, 3);
    await expectInactiveThumbnail(page, 1);
  });

  // Section 4 — Page navigation

  test("Navigates to a specific page via the page input", async ({ page }) => {
    const pageInput = getPageInput(page);
    await expect(pageInput).toBeVisible();
    await waitForPdfReadyAndDismissToast(page);

    await pageInput.fill("5");
    await pageInput.press("Enter");

    await expect(pageInput).toHaveValue("5", { timeout: 5000 });
  });

  test("Clamps out-of-range page numbers to valid range", async ({ page }) => {
    const pageInput = getPageInput(page);
    await expect(pageInput).toBeVisible();
    await waitForPdfReadyAndDismissToast(page);

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
    await waitForPdfReadyAndDismissToast(page);

    await scrollPdfViewer(page, 3000);

    await expect(async () => {
      const value = await pageInput.inputValue();
      expect(value).not.toBe("1");
    }).toPass({ timeout: 10000 });
  });
});

test.describe("PDF Links", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, PDF_LINKS_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pdf_with_links", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "pdf_with_links", exact: true })
      .dblclick();
    await expect(page.locator(".pdf-preview")).toBeVisible({ timeout: 10000 });
  });

  test("Shows a disclaimer modal when clicking an external link", async ({
    page,
  }) => {
    await waitForPdfReadyAndDismissToast(page);

    const modal = await clickExternalLinkAndWaitForModal(page);

    await expect(modal.locator(".c__modal__title")).toHaveText("External link");
    await expect(modal.locator(".pdf-preview__external-link")).toContainText(
      "example.com",
    );
    await expect(modal).toContainText("Do you want to continue?");
  });

  test("Opens external link in a new tab when confirming", async ({
    page,
    context,
  }) => {
    await waitForPdfReadyAndDismissToast(page);

    const modal = await clickExternalLinkAndWaitForModal(page);

    const [newPage] = await Promise.all([
      context.waitForEvent("page"),
      modal.getByRole("button", { name: "Yes" }).click(),
    ]);

    expect(newPage.url()).toContain("example.com");
    await newPage.close();
  });

  test("Does not open a new tab when declining the disclaimer", async ({
    page,
  }) => {
    await waitForPdfReadyAndDismissToast(page);

    const modal = await clickExternalLinkAndWaitForModal(page);

    await modal.getByRole("button", { name: "Cancel" }).click();

    await expect(modal).not.toBeAttached({ timeout: 5000 });
    await expect(page.locator(".pdf-preview")).toBeVisible();
  });

  test("Navigates to target page via an internal link without disclaimer", async ({
    page,
  }) => {
    await waitForPdfReadyAndDismissToast(page);

    await getInternalLink(page).click({ force: true });

    await expect(getDisclaimerModal(page)).not.toBeAttached({ timeout: 2000 });
    await expect(getPageInput(page)).toHaveValue("3", { timeout: 5000 });
  });
});

test.describe("PDF Security", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, PDF_JS_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pdf_with_js", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "pdf_with_js", exact: true })
      .dblclick();
    await expect(page.locator(".pdf-preview")).toBeVisible({ timeout: 10000 });
  });

  test("Does not execute JavaScript embedded in a PDF OpenAction", async ({
    page,
  }) => {
    let alertFired = false;
    page.on("dialog", () => {
      alertFired = true;
    });

    await waitForPdfReadyAndDismissToast(page);

    // Give any rogue script time to fire (it would trigger on document open)
    await page.waitForTimeout(1000);

    // The embedded JS calls app.alert("HACKED") — must never produce a dialog
    expect(alertFired).toBe(false);

    // The viewer itself should still be functional
    await expect(page.locator(".pdf-preview")).toBeVisible();
  });
});

test.describe("PDF Security — javascript: URI link", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, PDF_JS_LINK_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pdf_with_js_link", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "pdf_with_js_link", exact: true })
      .dblclick();
    await expect(page.locator(".pdf-preview")).toBeVisible({ timeout: 10000 });
  });

  test("Blocks javascript: URI links and does not show disclaimer modal", async ({
    page,
  }) => {
    let alertFired = false;
    page.on("dialog", async (dialog) => {
      alertFired = true;
      await dialog.dismiss();
    });

    await waitForPdfReadyAndDismissToast(page);

    // pdfjs should not render javascript: URIs as clickable annotations
    const annotationLinks = page.locator(
      ".annotationLayer section.linkAnnotation a",
    );
    await expect(annotationLinks).toHaveCount(0, { timeout: 5000 });

    // No alert/dialog should have fired
    expect(alertFired).toBe(false);

    // Even if a javascript: link were injected into the DOM, our handler
    // would block it. Simulate this by injecting a link and clicking it.
    await page.evaluate(() => {
      const annotLayer = document.querySelector(".annotationLayer");
      if (!annotLayer) return;
      const section = document.createElement("section");
      section.className = "linkAnnotation";
      const a = document.createElement("a");
      a.href = "javascript:alert('xss')";
      a.textContent = "injected";
      a.style.cssText =
        "position:absolute;top:0;left:0;width:50px;height:20px;";
      section.appendChild(a);
      annotLayer.appendChild(section);
    });

    const injectedLink = page
      .locator(".annotationLayer section.linkAnnotation a")
      .first();
    await injectedLink.click({ force: true });

    // The confirmation modal must NOT appear (unsafe protocol blocked)
    await expect(getDisclaimerModal(page)).not.toBeAttached({ timeout: 2000 });

    // Wait to ensure no alert fires even with rendering lag
    await page.waitForTimeout(2000);
    expect(alertFired).toBe(false);

    // The viewer should still be functional
    await expect(page.locator(".pdf-preview")).toBeVisible();
  });
});

test.describe("PDF Outdated Browser", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, PDF_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 10000 });
  });

  test("Shows outdated browser error when the PDF worker fails to initialize", async ({
    page,
  }) => {
    // Intercept the PDF worker script and replace it with one that throws,
    // simulating a browser where required APIs are missing.
    await page.route("**/pdf.worker.mjs", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/javascript",
        body: "throw new Error('Simulated worker init failure');",
      }),
    );

    await page.getByRole("cell", { name: "pv_cm", exact: true }).dblclick();

    const errorContainer = page.locator(".file-preview-unsupported");
    await expect(errorContainer).toBeVisible({ timeout: 15000 });

    await expect(errorContainer).toContainText(
      "Your browser is not supported",
    );
    await expect(errorContainer).toContainText(
      "For security reasons, the PDF viewer requires a recent browser",
    );

    await expect(page.locator(".pdf-preview__controls")).not.toBeAttached();
  });
});

test.describe("PDF Error Handling", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, PDF_CORRUPTED_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pdf_corrupted", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "pdf_corrupted", exact: true })
      .dblclick();
  });

  test("Displays an error message when opening a corrupted PDF", async ({
    page,
  }) => {
    const errorContainer = page.locator(".file-preview-unsupported");
    await expect(errorContainer).toBeVisible({ timeout: 15000 });

    await expect(errorContainer).toContainText(
      "An error occurred while loading the document.",
    );
    await expect(errorContainer).toContainText(
      "You can contact the support for help.",
    );
  });
});
