import path from "path";

import test, { expect } from "@playwright/test";

import { clearDb, login } from "../utils-common";
import { clickToMyFiles } from "../utils-navigate";
import { uploadFile } from "../utils/upload-utils";

const AUDIO_FILE_PATH = path.join(__dirname, "../assets/test-audio.mp3");

test.describe("Audio Preview", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);

    await uploadFile(page, AUDIO_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "test-audio", exact: true }),
    ).toBeVisible({ timeout: 10000 });

    await page
      .getByRole("cell", { name: "test-audio", exact: true })
      .dblclick();
    await expect(page.getByTestId("file-preview")).toBeVisible({
      timeout: 10000,
    });
  });

  test("Renders the AudioPlayer with the file title and source", async ({
    page,
  }) => {
    const player = page.locator(".audio-player");
    await expect(player).toBeVisible();

    await expect(player.locator(".audio-player__title")).toHaveText(
      "test-audio.mp3",
    );

    const audio = player.locator("audio");
    await expect(audio).toBeAttached();

    const src = await audio.getAttribute("src");
    expect(src).toBeTruthy();
    expect(src).toMatch(/test-audio/);
  });

  test("Hides the actions menu for audio files", async ({ page }) => {
    const filePreview = page.getByTestId("file-preview");
    await expect(filePreview.getByText("more_vert")).not.toBeVisible();
  });
});
