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
});
