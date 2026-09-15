import { expect } from "@playwright/test";
// Importing `MultiUserTest as test` as otherwise SonarCloud.io will complain about this file having no tests.
import { clearDb, login, MultiUserTest as test } from "./utils-common";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  closeShareModal,
  expectShareModal,
  openShareModal,
  selectLinkReach,
} from "./utils/share-utils";

/**
 * Scenario 1: authenticated user visits a restricted folder URL → sees request
 * access button on the 403 page, clicks it, success message appears and the
 * button is gone. The owner then opens the share modal and sees the pending request.
 */
test("authenticated user can request access from the 403 page and owner sees the pending request", async ({
  userA,
  userB,
}) => {
  await clearDb();
  await login(userA.page, "drive@example.com");
  await login(userB.page, "user@webkit.test");

  // User A (owner) creates a private folder.
  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await createFolderInCurrentFolder(userA.page, "Private folder");
  await navigateToFolder(userA.page, "Private folder", [
    "My files",
    "Private folder",
  ]);
  const folderUrl = userA.page.url();

  // User B visits the folder URL directly — gets redirected to /403.
  await userB.page.goto(folderUrl);
  await expect(
    userB.page.getByText("You don't have the necessary permissions"),
  ).toBeVisible();

  const requestButton = userB.page.getByRole("button", {
    name: "Request access",
  });
  await expect(requestButton).toBeVisible();

  // Clicking sends the request; the button disappears and the success message shows.
  await requestButton.click();
  await expect(requestButton).not.toBeVisible();
  await expect(
    userB.page.getByText("Your access request has been sent."),
  ).toBeVisible();

  // User A (owner) opens the share modal and sees the pending request from user B.
  await userA.page.reload();
  const shareModal = await openShareModal(userA.page);
  await expect(shareModal.getByText("Access requests")).toBeVisible();
  await expect(shareModal.getByText("user@webkit.test")).toBeVisible();

  await closeShareModal(userA.page);
});

/**
 * Scenario 2a: owner accepts a pending request → user B can now access the folder.
 */
test("owner can accept a pending access request and user can access the folder", async ({
  userA,
  userB,
}) => {
  await clearDb();
  await login(userA.page, "drive@example.com");
  await login(userB.page, "user@webkit.test");

  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await createFolderInCurrentFolder(userA.page, "Shared folder");
  await navigateToFolder(userA.page, "Shared folder", [
    "My files",
    "Shared folder",
  ]);
  const folderUrl = userA.page.url();

  // User B requests access.
  await userB.page.goto(folderUrl);
  await userB.page.getByRole("button", { name: "Request access" }).click();
  await expect(
    userB.page.getByText("Your access request has been sent."),
  ).toBeVisible();

  // User A (owner) opens the share modal and accepts the request.
  await userA.page.reload();
  const shareModal = await openShareModal(userA.page);
  await expect(shareModal.getByText("Access requests")).toBeVisible();
  await shareModal.getByRole("button", { name: "Accept" }).click();

  // The "Access requests" section disappears once there are no more pending requests.
  await expect(shareModal.getByText("Access requests")).not.toBeVisible();
  await closeShareModal(userA.page);

  // User B can now navigate to the folder directly — no 403 anymore.
  await userB.page.goto(folderUrl);
  await expect(userB.page).toHaveURL(folderUrl);
  await expect(
    userB.page.getByText("You don't have the necessary permissions"),
  ).not.toBeVisible();

  // User B opens the share modal and can see the members list with user A in it.
  const userBShareModal = await openShareModal(userB.page);
  const membersList = userBShareModal.getByTestId("members-list");
  await expect(membersList).toBeVisible();
  await expect(membersList.getByText("drive@example.com")).toBeVisible();
  await closeShareModal(userB.page);
});

/**
 * Scenario 2b: owner denies a pending request → user B still gets a 403.
 */
test("owner can deny a pending access request and user still gets a 403", async ({
  userA,
  userB,
}) => {
  await clearDb();
  await login(userA.page, "drive@example.com");
  await login(userB.page, "user@webkit.test");

  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await createFolderInCurrentFolder(userA.page, "Shared folder");
  await navigateToFolder(userA.page, "Shared folder", [
    "My files",
    "Shared folder",
  ]);
  const folderUrl = userA.page.url();

  // User B requests access.
  await userB.page.goto(folderUrl);
  await userB.page.getByRole("button", { name: "Request access" }).click();
  await expect(
    userB.page.getByText("Your access request has been sent."),
  ).toBeVisible();

  // User A (owner) opens the share modal and denies the request.
  await userA.page.reload();
  const shareModal = await openShareModal(userA.page);
  await expect(shareModal.getByText("Access requests")).toBeVisible();
  await shareModal.getByRole("button", { name: "Deny" }).click();

  // The "Access requests" section disappears once there are no more pending requests.
  await expect(shareModal.getByText("Access requests")).not.toBeVisible();
  await closeShareModal(userA.page);

  // User B visits the folder again — still gets a 403.
  await userB.page.goto(folderUrl);
  await expect(
    userB.page.getByText("You don't have the necessary permissions"),
  ).toBeVisible();
});

/**
 * Scenario 3: authenticated user can view a public/connected folder (via link)
 * but is not a member — the share modal shows the "cannot view" message and a
 * "Request access" button. After clicking, the button text changes to "Access
 * request sent" and it becomes disabled.
 */
test("user viewing a public folder sees cannot-view message and request access button in share modal", async ({
  userA,
  userB,
}) => {
  await clearDb();
  await login(userA.page, "drive@example.com");
  await login(userB.page, "user@webkit.test");

  // User A (owner) creates a folder and makes it publicly accessible.
  await userA.page.goto("/");
  await clickToMyFiles(userA.page);
  await createFolderInCurrentFolder(userA.page, "Public folder");
  await navigateToFolder(userA.page, "Public folder", [
    "My files",
    "Public folder",
  ]);
  await openShareModal(userA.page);
  await selectLinkReach(userA.page, "Public");
  await closeShareModal(userA.page);
  const folderUrl = userA.page.url();

  // User B visits the folder URL — they can view it because the link is "Public".
  await userB.page.goto(folderUrl);

  // User B clicks the "world" icon button (data-testid="share-button") that appears
  // in the breadcrumb for public folders. This opens the share modal without requiring
  // the "Share" dropdown option, which is only available to members.
  await userB.page.getByTestId("share-button").click();
  const shareModal = await expectShareModal(userB.page);

  // The ShareModal shows the built-in "cannot view" message (from ui-components).
  await expect(
    shareModal.getByText(
      "You can view this item but you need additional access to view its members or modify the settings.",
    ),
  ).toBeVisible();

  // The "Request access" button is present and enabled.
  const requestButton = shareModal.getByRole("button", {
    name: "Request access",
  });
  await expect(requestButton).toBeVisible();
  await expect(requestButton).toBeEnabled();

  // After clicking, the button becomes "Access request sent" and is disabled.
  await requestButton.click();
  await expect(
    shareModal.getByRole("button", { name: "Access request sent" }),
  ).toBeDisabled();
});
