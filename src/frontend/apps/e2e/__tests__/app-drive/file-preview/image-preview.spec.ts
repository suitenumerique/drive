import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "../utils-common";
import { clickToMyFiles } from "../utils-navigate";
import { uploadFile } from "../utils/upload-utils";

const IMAGE_FILE_PATH = path.join(__dirname, "../assets/test-image.png");

test.describe("Image Preview", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, IMAGE_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "test-image", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "test-image", exact: true })
      .dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });
  });

  test("Displays the image in the ImageViewer", async ({ page }) => {
    const viewer = page.locator(".image-viewer");
    await expect(viewer).toBeVisible();

    const image = viewer.locator("img.image-viewer__image");
    await expect(image).toBeVisible({ timeout: 5000 });

    const src = await image.getAttribute("src");
    expect(src).toBeTruthy();
    expect(src).toMatch(/test-image/);
  });

  test("Shows the actions menu (more_vert) for image files", async ({
    page,
  }) => {
    const filePreview = page.getByTestId("file-preview");
    const moreVertButton = filePreview.getByText("more_vert").locator("..");
    await expect(moreVertButton).toBeVisible();

    await moreVertButton.click();
    await expect(page.getByRole("menuitem", { name: "Print" })).toBeVisible();
  });

  test("Print action triggers the browser print dialog via a hidden iframe", async ({
    page,
    context,
  }) => {
    // Replace window.print on every iframe's contentWindow with a spy so the
    // test never opens a real OS print dialog. We patch the prototype getter
    // because the iframe is only created after the Print menu item is clicked,
    // so we have no direct reference to it at stub time.
    await page.evaluate(() => {
      (window as unknown as { __printCalled: boolean }).__printCalled = false;
      const descriptor = Object.getOwnPropertyDescriptor(
        HTMLIFrameElement.prototype,
        "contentWindow",
      );
      Object.defineProperty(HTMLIFrameElement.prototype, "contentWindow", {
        configurable: true,
        get() {
          const win = descriptor?.get?.call(this) as Window | null;
          // Patch each contentWindow exactly once — the getter is invoked
          // multiple times (onload handler, afterprint listener, focus, ...).
          if (win && !(win as unknown as { __patched?: boolean }).__patched) {
            (win as unknown as { __patched: boolean }).__patched = true;
            win.print = () => {
              (
                window as unknown as { __printCalled: boolean }
              ).__printCalled = true;
            };
          }
          return win;
        },
      });
    });

    const pagesBefore = context.pages().length;

    // Capture the preview URL shown by the ImageViewer so we can later check
    // the hidden print iframe loads the exact same file.
    const previewSrc = await page
      .locator(".image-viewer img.image-viewer__image")
      .getAttribute("src");
    expect(previewSrc).toBeTruthy();

    const filePreview = page.getByTestId("file-preview");
    const moreVertButton = filePreview.getByText("more_vert").locator("..");
    await moreVertButton.click();
    await page.getByRole("menuitem", { name: "Print" }).click();

    // The print utility appends a hidden iframe to <body>. It is the only
    // direct iframe child of body that we mark with aria-hidden.
    const hiddenIframe = page.locator('body > iframe[aria-hidden="true"]');
    await expect(hiddenIframe).toHaveCount(1, { timeout: 5000 });

    // The iframe's <img> must point to the same preview URL as the viewer —
    // i.e. we are about to print the file the user is currently looking at.
    const iframeImg = hiddenIframe.contentFrame().locator("img");
    await expect(iframeImg).toHaveAttribute("src", previewSrc!, {
      timeout: 5000,
    });

    // The <img> inside the iframe must actually load — otherwise print()
    // would fire on an empty document. naturalWidth is 0 until the browser
    // successfully decodes the image, so polling until it is > 0 proves
    // the image really loaded.
    await expect
      .poll(
        () =>
          iframeImg.evaluate((img: HTMLImageElement) => img.naturalWidth),
        { timeout: 5000 },
      )
      .toBeGreaterThan(0);

    // window.print on the iframe's contentWindow must have been called.
    await expect
      .poll(
        () =>
          page.evaluate(
            () =>
              (window as unknown as { __printCalled: boolean }).__printCalled,
          ),
        { timeout: 5000 },
      )
      .toBe(true);

    // No new tab should have been opened.
    expect(context.pages().length).toBe(pagesBefore);
  });

  test("Zoom keyboard shortcuts (+, -, 0) update the image transform", async ({
    page,
  }) => {
    const wrapper = page.locator(".image-viewer__image-wrapper");
    await expect(wrapper).toBeVisible({ timeout: 5000 });

    // Focus the container so the ImageViewer keyboard handler fires
    // (the handler checks e.target === containerRef.current).
    const container = page.locator(".image-viewer__container");
    await container.focus();

    const initialTransform = await wrapper.evaluate(
      (el) => (el as HTMLElement).style.transform,
    );
    const initialScale = parseFloat(
      initialTransform.match(/scale\(([^)]+)\)/)?.[1] ?? "NaN",
    );
    expect(Number.isFinite(initialScale)).toBe(true);

    await page.keyboard.press("=");
    await expect(async () => {
      const t = await wrapper.evaluate(
        (el) => (el as HTMLElement).style.transform,
      );
      const s = parseFloat(t.match(/scale\(([^)]+)\)/)?.[1] ?? "NaN");
      expect(s).toBeGreaterThan(initialScale);
    }).toPass({ timeout: 5000 });

    await page.keyboard.press("0");
    await expect(async () => {
      const t = await wrapper.evaluate(
        (el) => (el as HTMLElement).style.transform,
      );
      const s = parseFloat(t.match(/scale\(([^)]+)\)/)?.[1] ?? "NaN");
      expect(s).toBeCloseTo(initialScale, 2);
    }).toPass({ timeout: 5000 });
  });

  test("Clicking the blurry backdrop closes the preview", async ({ page }) => {
    const container = page.locator(".image-viewer__container");
    await expect(container).toBeVisible({ timeout: 5000 });

    // Top-left corner of the container sits in the 20% margin flex-space
    // around the centered image — i.e. the blurry backdrop.
    await container.click({ position: { x: 5, y: 5 } });

    await expect(page.getByTestId("file-preview")).toBeHidden({
      timeout: 5000,
    });
  });

  test("Clicking the image itself does not close the preview", async ({
    page,
  }) => {
    const wrapper = page.locator(".image-viewer__image-wrapper");
    await expect(wrapper).toBeVisible({ timeout: 5000 });

    await wrapper.click();

    // Preview must still be on screen — the click landed on a non-backdrop.
    await expect(page.getByTestId("file-preview")).toBeVisible();
  });

  test("Dragging across the image viewer does not close the preview", async ({
    page,
  }) => {
    const container = page.locator(".image-viewer__container");
    await expect(container).toBeVisible({ timeout: 5000 });

    const box = await container.boundingBox();
    if (!box) throw new Error("image-viewer__container has no bounding box");

    // Drive a pan-like gesture on the backdrop area. The ImageViewer's
    // click-capture guard must swallow the resulting click so it never
    // reaches the FilePreview backdrop handler.
    await page.mouse.move(box.x + 5, box.y + 5);
    await page.mouse.down();
    await page.mouse.move(box.x + 80, box.y + 80, { steps: 5 });
    await page.mouse.up();

    await expect(page.getByTestId("file-preview")).toBeVisible();
  });
});
