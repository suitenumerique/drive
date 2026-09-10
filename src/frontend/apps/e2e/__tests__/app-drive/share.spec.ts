import { test as base, BrowserContext, expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import {
  clickToMyFiles,
  clickToSharedWithMe,
  navigateToFolder,
} from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  clickCopyLinkButton,
  clickOnMemberItemRole,
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
import {
  clickOnBreadcrumbButtonAction,
  expectExplorerBreadcrumbs,
} from "./utils-explorer";
import { setupPosthogEventCapture } from "./utils/posthog-utils";

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
  await login(userA.page, "drive@drive.world");
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
    await login(userA.page, "drive@drive.world");
    await login(userB.page, "user@webkit.test");

    // User A creates a folder and shares it with User B
    await userA.page.goto("/");
    await clickToMyFiles(userA.page);
    await createFolderInCurrentFolder(userA.page, "Folder");
    await navigateToFolder(userA.page, "Folder", ["My files", "Folder"]);
    await shareCurrentItemWithWebkitUser(userA.page, "Editor");
    await closeShareModal(userA.page);
    await createFolderInCurrentFolder(userA.page, "Sub folder");
    await navigateToFolder(userA.page, "Sub folder", [
      "My files",
      "Folder",
      "Sub folder",
    ]);
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
    await login(userA.page, "drive@drive.world");
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
    await navigateToFolder(userA.page, "Sub folder", [
      "My files",
      "Folder",
      "Sub folder",
    ]);
    await openShareModal(userA.page);
    await expectLinkReachSelected(userA.page, "Connected");
    await expectAllowedLinkReach(
      userA.page,
      ["Connected", "Public"],
      ["Private"],
    );
  },
);

MultiUserTest("share a folder and posthog event is sent", async ({ userA }) => {
  await clearDb();
  await login(userA.page, "drive@drive.world");

  const { expectEventSent } = await setupPosthogEventCapture(userA.page);

  // User A creates a folder and shares it with User B
  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await createFolderInCurrentFolder(userA.page, "Folder");
  await navigateToFolder(userA.page, "Folder", ["My files", "Folder"]);
  await openShareModal(userA.page);
  await selectLinkReach(userA.page, "Connected");
  await expectLinkReachSelected(userA.page, "Connected");
  await clickCopyLinkButton(userA.page);
  await expectEventSent("click_copy_link");
});

MultiUserTest(
  "click parent folder link in share modal navigates to parent",
  async ({ userA, userB }) => {
    await clearDb();
    await login(userA.page, "drive@drive.world");
    await login(userB.page, "user@webkit.test");

    const { expectEventSent } = await setupPosthogEventCapture(userA.page);

    // User A creates a folder, shares it, and creates a sub folder
    await userA.page.goto("/");
    await clickToMyFiles(userA.page);
    await createFolderInCurrentFolder(userA.page, "Folder");
    await navigateToFolder(userA.page, "Folder", ["My files", "Folder"]);
    await shareCurrentItemWithWebkitUser(userA.page, "Editor");
    await closeShareModal(userA.page);
    await createFolderInCurrentFolder(userA.page, "Sub folder");
    await navigateToFolder(userA.page, "Sub folder", ["My files", "Folder", "Sub folder"]);

    // Open share modal on the sub folder and click the parent folder link
    const shareModal = await openShareModal(userA.page);
    await clickOnMemberItemRole(userA.page, "user@webkit.test");
    const parentFolderLink = userA.page.getByRole("button", {
      name: "the parent folder.",
    });
    await expect(parentFolderLink).toBeVisible();
    await parentFolderLink.click();

    // The share modal should close and the user should be redirected to the parent
    await expect(shareModal).not.toBeVisible();
    await expectExplorerBreadcrumbs(userA.page, ["My files", "Folder"]);

    // Verify the posthog click_redirect_to_parent_item event was sent
    await expectEventSent("click_redirect_to_parent_item");
  },
);
