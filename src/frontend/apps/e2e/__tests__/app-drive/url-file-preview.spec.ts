import test, { BrowserContext, expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import path from "path";
import { readFileSync } from "fs";

const grantClipboardPermissions = async (
  browserName: string,
  context: BrowserContext
) => {
  if (browserName === "chromium" || browserName === "webkit") {
    await context.grantPermissions(["clipboard-read"]);
  }
};

test("Share url leads to standalone file preview", async ({
  page,
  context,
  browserName,
}) => {
  // On the CI the evaluateHandle is not working with webkit.
  if (browserName === "webkit") {
    return;
  }
  grantClipboardPermissions(browserName, context);
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await expect(page.getByText("Drop your files here")).toBeVisible();

  //   Start waiting for file chooser before clicking. Note no await.
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Import" }).click();
  await page.getByRole("menuitem", { name: "Import files" }).click();

  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(path.join(__dirname, "/assets/pv_cm.pdf"));

  await expect(page.getByText("Drop your files here")).not.toBeVisible();
  await page
    .getByRole("button", { name: "More actions for pv_cm.pdf" })
    .nth(1)
    .click({ force: true });
  await page.getByRole("menuitem", { name: "Share" }).click();
  await page.getByRole("button", { name: "link Copy link" }).click();
  await expect(page.getByText("Copied to clipboard")).toBeVisible();

  // Get clipboard content after the link/button has been clicked
  const handle = await page.evaluateHandle(() =>
    navigator.clipboard.readText()
  );
  const clipboardContent = await handle.jsonValue();
  await page.goto(clipboardContent);

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();
  await expect(filePreview.getByText("pv_cm")).toBeVisible();
  await expect(
    filePreview
      .getByTestId("file-preview")
      .getByRole("button", { name: "close" })
  ).not.toBeVisible();
  await expect(filePreview.getByTestId("file-preview-nav")).not.toBeVisible();
});

test("Wrong url leads to 404 instead of standalone file preview", async ({
  page,
}) => {
  await login(page, "drive@example.com");
  await page.goto("http://localhost:3000/explorer/items/files/not_a_uuid");

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).not.toBeVisible();

  await page.getByText("The file you are looking for").click();
});
