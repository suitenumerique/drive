import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import path from "path";
import { clickToMyFiles } from "./utils-navigate";

test("Display HEIC not supported message when opening a HEIC file", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  // Use the real HEIC file from assets
  const heicFilePath = path.join(__dirname, "/assets/test-image.heic");

  // Upload the HEIC file
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Import" }).click();
  await page.getByRole("menuitem", { name: "Import files" }).click();

  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(heicFilePath);

  // Wait for the file to be uploaded and visible in the list
  await expect(page.getByText("Drop your files here")).not.toBeVisible();
  await expect(page.getByRole("cell", { name: "test-image.heic" })).toBeVisible(
    {
      timeout: 10000,
    }
  );

  // Click on the HEIC file to open the preview
  await page.getByRole("cell", { name: "test-image.heic" }).dblclick();

  // Check that the file preview is visible
  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();

  // Check that the HEIC-specific message is displayed
  await expect(
    filePreview.getByText("HEIC files are not yet supported for preview.")
  ).toBeVisible();
});
