import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import {
  clickToFavorites,
  clickToMyFiles,
  clickToRecent,
  navigateToFolder,
} from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  clickOnRowItemActions,
  getRowItemActions,
} from "./utils-embedded-grid";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import { PageOrLocator } from "./utils/types-utils";
import { starItem } from "./utils/starred-utils";

const PARENT = "Parent folder";
const CHILD = "Nested folder";
const ACTION = "Open parent folder";

/**
 * Opens an item's action menu and asserts the action is not offered in it. The
 * menu is first awaited on another entry, so an empty menu cannot pass.
 */
const expectActionIsNotOffered = async (
  page: PageOrLocator,
  itemName: string,
) => {
  const actions = await getRowItemActions(page, itemName);
  await actions.click({ force: true });
  await expect(
    page.getByRole("menuitem", { name: "Information" }),
  ).toBeVisible();
  await expect(page.getByRole("menuitem", { name: ACTION })).toBeHidden();
};

test.describe("Open parent folder", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
    await createFolderInCurrentFolder(page, PARENT);
    await navigateToFolder(page, PARENT, ["My files", PARENT]);
    await createFolderInCurrentFolder(page, CHILD);
  });

  test("navigates to the parent folder from Recents", async ({ page }) => {
    await clickToRecent(page);

    await clickOnRowItemActions(page, CHILD, ACTION);

    // Coming from Recents, the breadcrumb keeps the way back to it.
    await expectExplorerBreadcrumbs(page, ["Recents", PARENT]);
  });

  test("navigates to the parent folder from Starred", async ({ page }) => {
    await starItem(page, CHILD);
    await clickToFavorites(page);

    await clickOnRowItemActions(page, CHILD, ACTION);

    await expectExplorerBreadcrumbs(page, ["Starred", PARENT]);
  });

  test("is not offered for an item at the root of the workspace", async ({
    page,
  }) => {
    await clickToRecent(page);

    // PARENT sits at the root of "My files": it has no parent folder to open.
    await expectActionIsNotOffered(page, PARENT);
  });

  test("is not offered in a folder listing", async ({ page }) => {
    // Still inside PARENT, where the parent folder is already the page shown.
    await expectActionIsNotOffered(page, CHILD);
  });
});
