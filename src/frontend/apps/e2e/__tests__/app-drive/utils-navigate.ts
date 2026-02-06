import { Page, expect } from "@playwright/test";
import {
  expectDefaultRoute,
  expectExplorerBreadcrumbs,
} from "./utils-explorer";
import { getRowItem } from "./utils-embedded-grid";
import { clickOnItemInTree } from "./utils-tree";

export const clickToRecent = async (page: Page) => {
  await page.getByRole("link", { name: "Recents" }).click();
  await expectDefaultRoute(page, "Recents", "/explorer/items/recent");
};

export const clickToMyFiles = async (page: Page) => {
  await page.getByRole("link", { name: "My files" }).click();
  await expectDefaultRoute(page, "My files", "/explorer/items/my-files");
};

export const clickToSharedWithMe = async (page: Page) => {
  await page.getByRole("link", { name: "Shared with me" }).click();
  await expectDefaultRoute(
    page,
    "Shared with me",
    "/explorer/items/shared-with-me"
  );
};

export const clickToTrash = async (page: Page) => {
  await page.getByRole("link", { name: "Trash" }).click();
  const breadcrumbs = page.getByTestId("trash-page-breadcrumbs");
  await expect(breadcrumbs).toBeVisible();
  await expect(breadcrumbs).toContainText("Trash");
  const currentUrl = page.url();
  expect(currentUrl).toContain("/explorer/trash");
};

export const clickToFavorites = async (page: Page) => {
  await clickOnItemInTree(page, "Starred");
  await expectDefaultRoute(page, "Starred", "/explorer/items/favorites");
};

export const navigateToFolder = async (
  page: Page,
  folderName: string,
  expectedBreadcrumbs: string[]
) => {
  const folderItem = await getRowItem(page, folderName);
  await folderItem.dblclick();
  await expectExplorerBreadcrumbs(page, expectedBreadcrumbs);
};
