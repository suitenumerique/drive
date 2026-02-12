import { test as base, BrowserContext, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import {
  clickToMyFiles,
  clickToSharedWithMe,
  navigateToFolder,
} from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  closeShareModal,
  expectAllowedLinkReach,
  expectAllowedRoles,
  expectLinkReachSelected,
  openShareModal,
  selectLinkReach,
  shareCurrentItemWithWebkitUser,
} from "./utils/share-utils";
import {
  expectRowItem,
  expectRowItemIsNotVisible,
} from "./utils-embedded-grid";
import { clickOnBreadcrumbButtonAction } from "./utils-explorer";

type TwoUsers = {
  userA: { context: BrowserContext; page: Page };
  userB: { context: BrowserContext; page: Page };
};

const MultiUserTest = base.extend<TwoUsers>({
  userA: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await use({ context, page });
    await context.close();
  },

  userB: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await use({ context, page });
    await context.close();
  },
});

MultiUserTest("Share folder with user", async ({ userA, userB }) => {
  await clearDb();
  await login(userA.page, "drive@example.com");
  await login(userB.page, "user@webkit.test");

  // User A creates a folder and shares it with User B
  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await createFolderInCurrentFolder(userA.page, "Folder");

  // User B navigates to the shared with me folder and expects the folder to be not visible
  await userB.page.goto("/");
  await clickToSharedWithMe(userB.page);
  await expectRowItemIsNotVisible(userB.page, "Folder");

  // User A navigates to the folder and shares it with User B
  await navigateToFolder(userA.page, "Folder", ["My files", "Folder"]);
  await shareCurrentItemWithWebkitUser(userA.page, "Reader");

  // User B navigates to the shared with me folder and expects the folder to be visible
  await userB.page.goto("/");
  await clickToSharedWithMe(userB.page);
  await expectRowItem(userB.page, "Folder");
});

MultiUserTest(
  "share a folder and a sub folder with user and verify the roles",
  async ({ userA, userB }) => {
    await clearDb();
    await login(userA.page, "drive@example.com");
    await login(userB.page, "user@webkit.test");

    // User A creates a folder and shares it with User B
    await userA.page.goto("/");
    await clickToMyFiles(userA.page);
    await createFolderInCurrentFolder(userA.page, "Folder");
    await navigateToFolder(userA.page, "Folder", ["My files", "Folder"]);
    await shareCurrentItemWithWebkitUser(userA.page, "Editor");
    await closeShareModal(userA.page);
    await createFolderInCurrentFolder(userA.page, "Sub folder");
    await navigateToFolder(userA.page, "Sub folder", ["My files", "Folder", "Sub folder"]);
    await clickOnBreadcrumbButtonAction(userA.page, "Share");

    await expectAllowedRoles(
      userA.page,
      "user@webkit.test",
      ["Editor", "Administrator", "Owner"],
      ["Reader"],
    );
  },
);

MultiUserTest(
  "share a folder and verify the link reach",
  async ({ userA, userB }) => {
    await clearDb();
    await login(userA.page, "drive@example.com");
    await login(userB.page, "user@webkit.test");

    // User A creates a folder and shares it with User B
    await userA.page.goto("/");
    await clickToMyFiles(userA.page);
    await createFolderInCurrentFolder(userA.page, "Folder");
    await navigateToFolder(userA.page, "Folder", ["My files", "Folder"]);
    await openShareModal(userA.page);
    await selectLinkReach(userA.page, "Connected");
    await expectLinkReachSelected(userA.page, "Connected");
    await closeShareModal(userA.page);
    await createFolderInCurrentFolder(userA.page, "Sub folder");
    await navigateToFolder(userA.page, "Sub folder", ["My files", "Folder", "Sub folder"]);
    await openShareModal(userA.page);
    await expectLinkReachSelected(userA.page, "Connected");
    await expectAllowedLinkReach(
      userA.page,
      ["Connected", "Public"],
      ["Private"],
    );
  },
);
