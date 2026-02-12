import test from "@playwright/test";
import { clearDb, login } from "./utils-common";
import {
  clickToFavorites,
  clickToMyFiles,
  navigateToFolder,
} from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import { expectRowItem } from "./utils-embedded-grid";
import {
  starItem,
  unstarItem,
  verifyItemIsNotStarred,
  verifyItemIsStarred,
} from "./utils/starred-utils";
import { clickOnBreadcrumbButtonAction } from "./utils-explorer";

test("Add an item to starred and verify it's displayed in the starred tree and page", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "testFolder");
  await starItem(page, "testFolder");
  await verifyItemIsStarred(page, "testFolder");
  await clickToFavorites(page);
  await expectRowItem(page, "testFolder");
});

test("Remove an item from starred and verify it's not displayed in the starred tree and page", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "testFolder");
  await starItem(page, "testFolder");
  await verifyItemIsStarred(page, "testFolder");
  await clickToFavorites(page);
  await expectRowItem(page, "testFolder");
  await clickToMyFiles(page);
  await unstarItem(page, "testFolder");
  await verifyItemIsNotStarred(page, "testFolder");
});

test("Add an item to starred and one of it's children to starred and verify it's displayed in the starred tree and page", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "John");
  await navigateToFolder(page, "John", ["My files", "John"]);
  await createFolderInCurrentFolder(page, "Doe");
  await clickOnBreadcrumbButtonAction(page, "Star");
  await starItem(page, "Doe");
  await verifyItemIsStarred(page, "John");
  await verifyItemIsStarred(page, "Doe");
});
