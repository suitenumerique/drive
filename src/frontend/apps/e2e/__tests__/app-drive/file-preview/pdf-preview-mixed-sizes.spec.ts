import path from "path";

import test, { expect } from "@playwright/test";
import type { Page, Locator } from "@playwright/test";

import { clearDb, login } from "../utils-common";
import { clickToMyFiles } from "../utils-navigate";
import { uploadFile } from "../utils/upload-utils";

const MIXED_PDF_PATH = path.join(
  __dirname,
  "../assets/mixed_page_sizes.pdf",
);

// Known ratios (height / width) of each page in mixed_page_sizes.pdf.
// Derived from the PDF MediaBox entries with pdf-lib; see assets directory.
const EXPECTED_RATIOS = [
  1.414, 0.707, 1.294, 1.647, 0.707, 1.419, 0.709, 1.545, 1.412, 0.704, 1.0,
  0.286, 4.0, 1.0, 1.414, 1.56, 1.414,
];

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

function getPageInput(page: Page): Locator {
  return page.locator('input[aria-label="Current page"]');
}

function getRenderedPage(page: Page, pageNum: number): Locator {
  return page.locator(
    `.pdf-preview__container .react-pdf__Page[data-page-number="${pageNum}"]`,
  );
}

function getRenderedThumbnail(page: Page, pageNum: number): Locator {
  return page.locator(
    `.pdf-preview__sidebar [data-thumb-page="${pageNum}"] .react-pdf__Thumbnail`,
  );
}

async function openSidebar(page: Page) {
  const toggle = page.locator('button[aria-label="Toggle sidebar"]');
  await toggle.dispatchEvent("click");
  await expect(page.locator("[data-thumb-page]").first()).toBeVisible({
    timeout: 10000,
  });
}

async function goToPage(page: Page, pageNum: number) {
  const pageInput = getPageInput(page);
  await pageInput.fill(String(pageNum));
  await pageInput.press("Enter");
}

async function expectRatio(
  locator: Locator,
  expectedRatio: number,
  // 3% tolerance — canvas dims round to whole pixels, which is material on
  // extreme ratios like 0.286 (wide banner) and 4.0 (tall strip).
  tolerance = 0.03,
) {
  await expect(async () => {
    const box = await locator.boundingBox();
    expect(box).toBeTruthy();
    const ratio = box!.height / box!.width;
    expect(Math.abs(ratio - expectedRatio)).toBeLessThanOrEqual(
      Math.max(tolerance, expectedRatio * tolerance),
    );
  }).toPass({ timeout: 10000 });
}

async function expectRenderedRatio(
  page: Page,
  pageNum: number,
  expectedRatio: number,
) {
  await expectRatio(getRenderedPage(page, pageNum), expectedRatio);
}

test.describe("PDF Preview — mixed page sizes", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, MIXED_PDF_PATH);
    await expect(
      page.getByRole("cell", { name: "mixed_page_sizes", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "mixed_page_sizes", exact: true })
      .dblclick();
    await expect(page.locator(".pdf-preview")).toBeVisible({ timeout: 10000 });
    await waitForPdfReady(page);
    await dismissToast(page);
  });

  test("renders the first page at its actual aspect ratio (A4 portrait)", async ({
    page,
  }) => {
    await expectRenderedRatio(page, 1, EXPECTED_RATIOS[0]);
  });

  test("scrollToPage(2) lands on a landscape page and it renders at its real aspect ratio", async ({
    page,
  }) => {
    const pageInput = getPageInput(page);
    await pageInput.fill("2");
    await pageInput.press("Enter");
    await expect(pageInput).toHaveValue("2", { timeout: 5000 });

    // Landscape A4: width > height → ratio ~0.707
    await expectRenderedRatio(page, 2, EXPECTED_RATIOS[1]);

    const landscape = await getRenderedPage(page, 2).boundingBox();
    const portrait = await getRenderedPage(page, 1).boundingBox();
    expect(landscape).toBeTruthy();
    expect(portrait).toBeTruthy();
    // Fit-to-width: both pages use the same rendered width (±1 px canvas rounding).
    expect(Math.abs(landscape!.width - portrait!.width)).toBeLessThanOrEqual(1);
    // Landscape page is visibly shorter than its portrait neighbour.
    expect(landscape!.height).toBeLessThan(portrait!.height);
  });

  test("scrollToPage(13) lands on an extreme-ratio page (tall strip)", async ({
    page,
  }) => {
    const pageInput = getPageInput(page);
    await pageInput.fill("13");
    await pageInput.press("Enter");
    await expect(pageInput).toHaveValue("13", { timeout: 5000 });

    // Page 13: 300x1200 → ratio 4.0 (very tall)
    await expectRenderedRatio(page, 13, EXPECTED_RATIOS[12]);
  });

  test("thumbnail and main page render at matching per-page aspect ratios", async ({
    page,
  }) => {
    await openSidebar(page);

    // Five pages covering portrait, landscape, wide-banner, tall-strip,
    // and square — spans the full spectrum of ratios the cache has to
    // handle. For each: navigate (which scrolls both viewer and sidebar
    // to the page), then assert the rendered aspect ratio on both the
    // main PdfPageViewer and the sidebar thumbnail.
    const cases = [
      { page: 1, ratio: EXPECTED_RATIOS[0] }, // A4 portrait
      { page: 2, ratio: EXPECTED_RATIOS[1] }, // A4 landscape
      { page: 12, ratio: EXPECTED_RATIOS[11] }, // 1400×400 wide banner
      { page: 13, ratio: EXPECTED_RATIOS[12] }, // 300×1200 tall strip
      { page: 14, ratio: EXPECTED_RATIOS[13] }, // 150×150 square
    ];

    // Thumbnails are virtualized, so only rows in overscan are in the DOM.
    // Capture each thumb's height as we navigate so we can compare portrait
    // vs landscape after the loop (when page 1's thumb is no longer mounted).
    const capturedThumbHeights: Record<number, number> = {};

    for (const c of cases) {
      await goToPage(page, c.page);
      await expect(getPageInput(page)).toHaveValue(String(c.page), {
        timeout: 5000,
      });
      // Thumbnail must be in the DOM (sidebar auto-scrolls to current page).
      await expect(getRenderedThumbnail(page, c.page)).toBeVisible({
        timeout: 10000,
      });
      await expectRenderedRatio(page, c.page, c.ratio);
      await expectRatio(getRenderedThumbnail(page, c.page), c.ratio);
      const box = await getRenderedThumbnail(page, c.page).boundingBox();
      expect(box).toBeTruthy();
      capturedThumbHeights[c.page] = box!.height;
    }

    // Guardrail: if per-page thumbnail heights weren't wired up, every
    // thumb would share the same row height and the portrait/landscape
    // thumbs would be indistinguishable. Landscape (p2 ratio ~0.707)
    // must be meaningfully shorter than portrait (p1 ratio ~1.414).
    expect(capturedThumbHeights[1]).toBeGreaterThan(
      capturedThumbHeights[2] * 1.5,
    );
  });

  test("page-input jumps land precisely on target across mixed ratios", async ({
    page,
  }) => {
    // Exercises ensurePageDimensions: each jump awaits the prefix's real
    // dimensions before computing the scroll offset, so the viewport
    // center lands inside the requested page even when predecessors
    // haven't been measured yet. Without the await, the first jump
    // (to page 13) used to land on page 14.
    const pageInput = getPageInput(page);
    for (const target of [13, 5, 17, 2, 11]) {
      await pageInput.fill(String(target));
      await pageInput.press("Enter");
      await expect(pageInput).toHaveValue(String(target), { timeout: 5000 });
    }
  });

  test("virtual-list total height matches the sum of per-page heights", async ({
    page,
  }) => {
    // Walk every page once so the lazy dim cache is populated.
    const pageInput = getPageInput(page);
    for (const p of [2, 5, 8, 11, 13, 15, 17, 1]) {
      await pageInput.fill(String(p));
      await pageInput.press("Enter");
      await expect(pageInput).toHaveValue(String(p), { timeout: 5000 });
    }

    const firstBox = await getRenderedPage(page, 1).boundingBox();
    expect(firstBox).toBeTruthy();
    const renderedWidth = firstBox!.width;

    // Sum of expected content heights (fit-to-width × each page's ratio).
    const expectedContentHeight = EXPECTED_RATIOS.reduce(
      (sum, r) => sum + renderedWidth * r,
      0,
    );

    const gridInner = page
      .locator(
        ".pdf-preview__container .ReactVirtualized__Grid__innerScrollContainer",
      )
      .first();

    await expect(async () => {
      const h = await gridInner.evaluate((el) =>
        parseFloat(getComputedStyle(el as HTMLElement).height),
      );
      // Every row reserves PAGE_GAP=16 above (paddingTop); the last row
      // additionally reserves PAGE_GAP below it → N+1 gaps total.
      const expectedTotal =
        expectedContentHeight + 16 * (EXPECTED_RATIOS.length + 1);
      // 5% tolerance: react-pdf canvas rounding + scroll-anchor jitter.
      expect(Math.abs(h - expectedTotal) / expectedTotal).toBeLessThanOrEqual(
        0.05,
      );
    }).toPass({ timeout: 15000 });
  });
});
