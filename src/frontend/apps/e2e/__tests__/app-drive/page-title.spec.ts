import test, { expect } from "@playwright/test";

import { clearDb, login } from "./utils-common";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  clickToFavorites,
  clickToMyFiles,
  clickToRecent,
  clickToSharedWithMe,
  clickToTrash,
  navigateToFolder,
} from "./utils-navigate";

const FOLDER_NAME = "Title folder";

test("The tab title names the current page and the application", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");

  await clickToRecent(page);
  await expect(page).toHaveTitle("Recents | Drive");

  await clickToSharedWithMe(page);
  await expect(page).toHaveTitle("Shared with me | Drive");

  await clickToFavorites(page);
  await expect(page).toHaveTitle("Starred | Drive");

  await clickToTrash(page);
  await expect(page).toHaveTitle("Trash | Drive");

  await clickToMyFiles(page);
  await expect(page).toHaveTitle("My files | Drive");

  // A folder uses its own name.
  await createFolderInCurrentFolder(page, FOLDER_NAME);
  await navigateToFolder(page, FOLDER_NAME, ["My files", FOLDER_NAME]);
  await expect(page).toHaveTitle(`${FOLDER_NAME} | Drive`);
});

test("The error pages name their message and the application", async ({
  page,
}) => {
  await page.goto("/401");
  await expect(page).toHaveTitle(
    "You need to be logged in to access the documents. | Drive",
  );

  await page.goto("/403");
  await expect(page).toHaveTitle(
    "You don't have the necessary permissions to access this page. | Drive",
  );
});

test.describe("in French", () => {
  test.use({ locale: "fr-FR" });

  test("My files is titled Mes fichiers | Fichiers", async ({ page }) => {
    await clearDb();
    await login(page, "drive-fr@example.com");
    await page.goto("/explorer/items/my-files");
    await expect(page.getByText("Cet onglet est vide")).toBeVisible({
      timeout: 10000,
    });
    await expect(page).toHaveTitle("Mes fichiers | Fichiers");
  });
});
