import { expect, Page } from "@playwright/test";
// Importing `MultiUserTest as test` as otherwise SonarCloud.io will complain about this file having no tests.
import { clearDb, login, MultiUserTest as test } from "./utils-common";
import {
  clickToMyFiles,
  clickToSharedWithMe,
  navigateToFolder,
} from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import { shareCurrentItemWithWebkitUser } from "./utils/share-utils";
import {
  clickOnRowItemActions,
  expectRowItem,
  expectRowItemIsNotVisible,
} from "./utils-embedded-grid";
import { expectDefaultRoute } from "./utils-explorer";

const createAndShareFolder = async (
  userA: Page,
  userB: Page,
  folderName: string,
  role: "Reader" | "Editor" | "Administrator",
) => {
  await login(userA, "drive@example.com");
  await login(userB, "user@webkit.test");
  await userA.goto("/");
  await clickToMyFiles(userA);
  await createFolderInCurrentFolder(userA, folderName);
  await navigateToFolder(userA, folderName, ["My files", folderName]);
  await shareCurrentItemWithWebkitUser(userA, role);
};

test("User can leave a shared folder from the row actions menu", async ({
  userA,
  userB,
}) => {
  await clearDb();
  await createAndShareFolder(userA.page, userB.page, "Shared Folder", "Editor");

  // User B sees the folder in "Shared with me"
  await userB.page.goto("/");
  await clickToSharedWithMe(userB.page);
  await expectRowItem(userB.page, "Shared Folder");

  // User B leaves the folder
  await clickOnRowItemActions(userB.page, "Shared Folder", "Leave");
  await userB.page.getByRole("button", { name: "Leave" }).click();

  // User B is redirected to "Shared with me" and the folder is gone
  await expectDefaultRoute(
    userB.page,
    "Shared with me",
    "/explorer/items/shared-with-me",
  );
  await expectRowItemIsNotVisible(userB.page, "Shared Folder");
});

test("Cancelling the leave modal keeps the item visible", async ({
  userA,
  userB,
}) => {
  await clearDb();
  await createAndShareFolder(userA.page, userB.page, "Shared Folder", "Reader");

  // User B opens the leave modal then cancels
  await userB.page.goto("/");
  await clickToSharedWithMe(userB.page);
  await expectRowItem(userB.page, "Shared Folder");

  await clickOnRowItemActions(userB.page, "Shared Folder", "Leave");
  await userB.page.getByRole("button", { name: "Cancel" }).click();

  // The folder is still visible
  await expectRowItem(userB.page, "Shared Folder");
});

test("Owner still sees the folder after another user leaves", async ({
  userA,
  userB,
}) => {
  await clearDb();
  await createAndShareFolder(userA.page, userB.page, "Shared Folder", "Editor");

  // User B leaves
  await userB.page.goto("/");
  await clickToSharedWithMe(userB.page);
  await clickOnRowItemActions(userB.page, "Shared Folder", "Leave");
  await userB.page.getByRole("button", { name: "Leave" }).click();
  await expectRowItemIsNotVisible(userB.page, "Shared Folder");

  // User A's folder is unaffected
  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await expectRowItem(userA.page, "Shared Folder");
});

test("Leave option is not shown to the folder owner", async ({ userA }) => {
  await clearDb();
  await login(userA.page, "drive@example.com");
  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await createFolderInCurrentFolder(userA.page, "My Folder");

  // Open the row actions for the owner — "Leave" should not appear
  const actions = userA.page
    .getByRole("button", {
      name: "More actions for My Folder",
      exact: true,
    })
    .nth(1);
  await actions.click({ force: true });
  await expect(
    userA.page.getByRole("menuitem", { name: "Leave" }),
  ).not.toBeVisible();
});
