import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import path from "path";

test("Open file with Enter key on desktop", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await expect(page.getByText("Drop your files here")).toBeVisible();

  // Use a pdf file from assets
  const pv_cm = path.join(__dirname, "/assets/pv_cm.pdf");

  // Upload the pdf to test opening with Enter key
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Import" }).click();
  await page.getByRole("menuitem", { name: "Import files" }).click();

  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(pv_cm);

  // Wait for the file to be uploaded and visible in the list
  await expect(page.getByText("Drop your files here")).not.toBeVisible();
  await expect(page.getByRole("cell", { name: "pv_cm.pdf" })).toBeVisible(
    {
      timeout: 10000,
    }
  );

  // Click on the PDF file to open the preview with the Enter key down
  await page.getByRole("cell", { name: "pv_cm.pdf" })
  await page.keyboard.down("ArrowDown");
  await page.keyboard.down("Enter");

  // Check that the file preview is visible
  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();
});

test("Open folder with Enter key", async ({ page }) => {
  await clearDb();
  await login(page, "drive@example.com");

  await page.goto("/");

  // Create a new folder to test opening with Enter key
  await expect(page.getByText("Drop your files here")).toBeVisible();
  await expect(page.getByRole("cell", { name: "My first folder" })).not.toBeVisible();
  await page.getByRole("button", { name: "add Create" }).click();
  await page.getByText("New folder").click();
  await page.getByRole("textbox", { name: "Folder name" }).fill("My first folder");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByText("Drop your files here")).not.toBeVisible();
  await expect(page.getByRole("cell", { name: "My first folder", exact: true })).toBeVisible();
  await page.getByRole("cell", { name: "My first folder" })
  // Set the folder as focused and press Enter to open it
  await page.keyboard.down("ArrowDown");
  await page.keyboard.down("Enter");

  await expectExplorerBreadcrumbs(page, ["My workspace", "My first folder"]);
});
