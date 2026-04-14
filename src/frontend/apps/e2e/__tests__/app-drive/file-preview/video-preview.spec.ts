import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "../utils-common";
import { clickToMyFiles } from "../utils-navigate";
import { uploadFile } from "../utils/upload-utils";

const VIDEO_FILE_PATH = path.join(__dirname, "../assets/test-video.mp4");

test.describe("Video Preview", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, VIDEO_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "test-video", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "test-video", exact: true })
      .dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });
  });

  test("Renders the VideoPlayer inside the video wrapper", async ({ page }) => {
    const wrapper = page.locator(".video-preview-viewer-container");
    await expect(wrapper).toBeVisible();

    const videoPlayer = wrapper.locator(".video-player");
    await expect(videoPlayer).toBeVisible();

    const video = videoPlayer.locator("video.video-player__video");
    await expect(video).toBeAttached();

    const src = await video.getAttribute("src");
    expect(src).toBeTruthy();
    expect(src).toMatch(/test-video/);
  });

  test("Shows custom controls (not native) when the video is loaded", async ({
    page,
  }) => {
    const video = page.locator("video.video-player__video");
    await expect(video).toBeAttached();

    // The component sets controls={false} on the <video> and renders its own UI.
    const hasNativeControls = await video.evaluate(
      (el) => (el as HTMLVideoElement).controls,
    );
    expect(hasNativeControls).toBe(false);

    // Custom controls bar should be visible.
    await expect(page.locator(".video-player__controls")).toBeVisible({
      timeout: 5000,
    });
  });

  test("Hides the actions menu for video files", async ({ page }) => {
    const filePreview = page.getByTestId("file-preview");
    await expect(filePreview.getByText("more_vert")).not.toBeVisible();
  });
});
