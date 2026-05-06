/**
 * Smoke tests for file-preview integration in drive.
 * Verifies the upload -> open preview -> basic render path.
 * Detailed component behavior is tested in ui-kit via Playwright CT.
 */
import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { uploadFile } from "./utils/upload-utils";

const ASSETS = path.join(__dirname, "./assets");

test.describe("File Preview Smoke Tests", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
  });

  test("PDF smoke — upload and open shows PDF viewer", async ({ page }) => {
    await uploadFile(page, path.join(ASSETS, "pv_cm.pdf"));
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page.getByRole("cell", { name: "pv_cm", exact: true }).dblclick();
    await expect(page.locator(".pdf-preview")).toBeVisible({ timeout: 10000 });
    await expect(page.locator(".react-pdf__Page").first()).toBeVisible({
      timeout: 10000,
    });

    await expect(
      page
        .locator(".textLayer")
        .getByText("PROCÈS VERBAL DU CONSEIL MUNICIPAL")
        .first(),
    ).toBeAttached({ timeout: 10000 });
  });

  test("Image smoke — upload and open shows image viewer", async ({ page }) => {
    await uploadFile(page, path.join(ASSETS, "test-image.png"));
    await expect(
      page.getByRole("cell", { name: "test-image", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "test-image", exact: true })
      .dblclick();
    await expect(
      page.locator(".image-viewer img.image-viewer__image"),
    ).toBeVisible({ timeout: 10000 });
  });

  test("Video smoke — upload and open shows video player", async ({ page }) => {
    await uploadFile(page, path.join(ASSETS, "test-video.mp4"));
    await expect(
      page.getByRole("cell", { name: "test-video", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "test-video", exact: true })
      .dblclick();
    await expect(page.locator("video.video-player__video")).toBeAttached({
      timeout: 10000,
    });
  });

  test("Audio smoke — upload and open shows audio player", async ({ page }) => {
    await uploadFile(page, path.join(ASSETS, "test-audio.mp3"));
    await expect(
      page.getByRole("cell", { name: "test-audio", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "test-audio", exact: true })
      .dblclick();
    await expect(page.locator(".audio-player audio")).toBeAttached({
      timeout: 10000,
    });
  });

  test("Navigation smoke — prev/next buttons work across files", async ({
    page,
  }) => {
    await uploadFile(page, path.join(ASSETS, "pv_cm.pdf"));
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await uploadFile(page, path.join(ASSETS, "test-image.png"));
    await expect(
      page.getByRole("cell", { name: "test-image", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page.getByRole("cell", { name: "pv_cm", exact: true }).dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });

    const title = page.locator("h1.file-preview__title");
    await expect(title).toHaveText("pv_cm");

    const nextButton = page.locator(".file-preview__next-button button");
    const prevButton = page.locator(".file-preview__previous-button button");

    const nextDisabled = await nextButton.isDisabled();
    if (!nextDisabled) {
      await nextButton.click();
    } else {
      await prevButton.click();
    }
    await expect(title).toHaveText("test-image");
  });
});
