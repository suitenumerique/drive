import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import path from "path";
import { clickToMyFiles } from "./utils-navigate";
import { uploadFile } from "./utils/upload-utils";
import { grantClipboardPermissions } from "./utils/various-utils";

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
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  //   Start waiting for file chooser before clicking. Note no await.
  await uploadFile(page, path.join(__dirname, "/assets/pv_cm.pdf"));

  await expect(page.getByText("This tab is empty")).not.toBeVisible();
  await page
    .getByRole("button", { name: "More actions for pv_cm.pdf" })
    .nth(1)
    .click({ force: true });
  await page.getByRole("menuitem", { name: "Share" }).click();
  await page.getByRole("button", { name: "link Copy link" }).click();
  await expect(page.getByText("Copied to clipboard")).toBeVisible();

  // Get clipboard content after the link/button has been clicked
  const handle = await page.evaluateHandle(() =>
    navigator.clipboard.readText(),
  );
  const clipboardContent = await handle.jsonValue();
  await page.goto(clipboardContent);

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();
  await expect(filePreview.getByText("pv_cm")).toBeVisible();
  await expect(
    filePreview
      .getByTestId("file-preview")
      .getByRole("button", { name: "close" }),
  ).not.toBeVisible();
  await expect(filePreview.getByTestId("file-preview-nav")).not.toBeVisible();
});

test("Wrong url leads to 404 instead of standalone file preview", async ({
  page,
}) => {
  await login(page, "drive@example.com");
  // This uuid is valid but does not exist in the database.
  await page.goto(
    "http://localhost:3000/explorer/items/files/c36ee34b-56c8-460b-b5fc-22245c5a3da4",
  );

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).not.toBeVisible();

  await page.getByText("The file you are looking for").click();
});
