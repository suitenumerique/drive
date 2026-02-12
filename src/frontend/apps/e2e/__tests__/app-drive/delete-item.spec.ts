import { clearDb, login } from "./utils-common";
import { expect } from "@playwright/test";
import test from "@playwright/test";
import { createFolderInCurrentFolder, deleteCurrentFolder } from "./utils-item";
import {
  expectDefaultRoute,
  expectExplorerBreadcrumbs,
} from "./utils-explorer";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";

test("Checks that if one of the parents of the current folder is deleted, it redirects to the highest parent", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "Test");
  await navigateToFolder(page, "Test", ["My files", "Test"]);
  const testUrl = page.url();
  await createFolderInCurrentFolder(page, "SubTest");
  await navigateToFolder(page, "SubTest", ["My files", "Test", "SubTest"]);
  await deleteCurrentFolder(page);
  await expect(page).toHaveURL(testUrl);
  await expectExplorerBreadcrumbs(page, ["My files", "Test"]);
});

test("Check that if we delete the current folder, it redirects to the parent folder", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "Test");
  await navigateToFolder(page, "Test", ["My files", "Test"]);
  await deleteCurrentFolder(page);
  await expectDefaultRoute(page, "My files", "/explorer/items/my-files");
});
