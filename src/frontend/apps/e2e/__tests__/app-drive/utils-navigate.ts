import { Page, expect } from "@playwright/test";
import {
  expectDefaultRoute,
  expectExplorerBreadcrumbs,
} from "./utils-explorer";
import { getRowItem } from "./utils-embedded-grid";
import { clickOnItemInTree } from "./utils-tree";

// The same names are now links in the breadcrumb. These helpers open the
// sidebar entry.
const clickSidebarLink = (page: Page, name: string) =>
  page
    .locator(".explorer__tree__nav")
    .getByRole("link", { name, exact: true })
    .click();

export const clickToRecent = async (page: Page) => {
  await clickSidebarLink(page, "Recents");
  await expectDefaultRoute(page, "Recents", "/explorer/items/recent");
};

export const clickToMyFiles = async (page: Page) => {
  await clickSidebarLink(page, "My files");
  await expectDefaultRoute(page, "My files", "/explorer/items/my-files");
};

export const clickToSharedWithMe = async (page: Page) => {
  await clickSidebarLink(page, "Shared with me");
  await expectDefaultRoute(
    page,
    "Shared with me",
    "/explorer/items/shared-with-me"
  );
};

export const clickToTrash = async (page: Page) => {
  await clickSidebarLink(page, "Trash");
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
