import path from "path";
import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { getRowItem } from "./utils-embedded-grid";
import { uploadFile } from "./utils/upload-utils";
import { grantClipboardPermissions } from "./utils/various-utils";

test("Copy and paste works in wopi editor", async ({ page, context, browserName }) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  grantClipboardPermissions(browserName, context);
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  //   Start waiting for file chooser before clicking. Note no await.
  await uploadFile(page, path.join(__dirname, "/assets/empty_doc.docx"));

  // Wait for the file to be uploaded and visible in the list
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  // Click on the file to open the preview
  const row = await getRowItem(page, "empty_doc");
  await row.dblclick();

  // Check that the file preview is visible
  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();

  const wopiIframe = filePreview.locator('iframe[name="office_frame"]');
  await expect(wopiIframe).toBeVisible();

  await expect(
    page
      .locator('iframe[name="office_frame"]')
      .contentFrame()
      .locator('iframe[name="iframe-welcome-form"]')
      .contentFrame()
      .getByRole("heading", { name: "Explore The New" }),
  ).toBeVisible();

  await page
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator('iframe[name="iframe-welcome-form"]')
    .contentFrame()
    .getByRole("button", { name: "Close" })
    .click();

  const canvas = page
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator('canvas[id="document-canvas"]');
  await expect(canvas).toBeVisible();

  // The editor zone is a canvas, so we need to take a screenshot of it.
  await expect(canvas).toHaveScreenshot("empty-doc-canvas.png", {
    maxDiffPixelRatio: 0.01,
  });
  await page
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator(".leaflet-layer")
    .click({ force: true });
  await page.waitForTimeout(1000);
  await page
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator("#clipboard-area")
    .press("ControlOrMeta+a");
  await page.waitForTimeout(1000);
  await page.keyboard.press(`ControlOrMeta+KeyC`);
  await page.waitForTimeout(1000);
  await page
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator("#clipboard-area")
    .press("ArrowRight");
  await page.waitForTimeout(1000);
  await page.keyboard.press(`ControlOrMeta+KeyV`);
  await page.waitForTimeout(1000);
  await expect(canvas).toHaveScreenshot("empty-doc-canvas-after-paste.png", {
    maxDiffPixelRatio: 0.01,
  });
});
