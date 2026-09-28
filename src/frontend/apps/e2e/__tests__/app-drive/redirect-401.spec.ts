import test, { expect } from "@playwright/test";
import { clearDb, keyCloakSignIn, login } from "./utils-common";
import { createFolderInCurrentFolder } from "./utils-item";
import { navigateToFolder } from "./utils-navigate";

test("Redirects to /401 when session cookies are cleared then re-login and get redirected to the folder", async ({
  page,
  context,
}) => {
  await clearDb();
  await page.goto("/");
  await keyCloakSignIn(page, "drive", "drive");

  await createFolderInCurrentFolder(page, "Secret folder");
  await navigateToFolder(page, "Secret folder", ["My files", "Secret folder"]);
  const folderUrl = page.url();

  await context.clearCookies();

  await page.reload();

  await expect(page).toHaveURL(/.*\/401/, { timeout: 10000 });
  await expect(
    page.getByText("You need to be logged in to access the documents."),
  ).toBeVisible();

  await page
    .locator(".drive__generic-disclaimer")
    .getByRole("button", { name: "Login" })
    .click();

  await keyCloakSignIn(page, "drive", "drive", false);

  await expect(page).toHaveURL(folderUrl, { timeout: 10000 });
});
