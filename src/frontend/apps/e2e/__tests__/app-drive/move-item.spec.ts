import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";
import { clickOnRowItemActions, getRowItem } from "./utils-embedded-grid";
import {
  acceptMoveItem,
  clickAndAcceptMoveToRoot,
  getMoveFolderModal,
  searchAndSelectItem,
} from "./utils/move-utils";
import { createFolderInCurrentFolder } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";

test("Move an item to a new folder", async ({ page }) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "John");
  await createFolderInCurrentFolder(page, "Doe");
  const JohnRow = await getRowItem(page, "John");
  await expect(JohnRow).toBeVisible();
  await clickOnRowItemActions(page, "John", "Move");
  const moveFolderModal = await getMoveFolderModal(page);
  const DoeRow = await getRowItem(moveFolderModal, "Doe");
  await DoeRow.click();
  await acceptMoveItem(page);
  await expect(JohnRow).not.toBeVisible();
});

test("Show an error toast when the server rejects the move", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "John");
  await createFolderInCurrentFolder(page, "Doe");

  // Reject the move server-side (e.g. quota gate on move-to-root).
  await page.route("**/api/v1.0/items/*/move/", (route) =>
    route.fulfill({
      status: 403,
      contentType: "application/json",
      body: JSON.stringify({
        type: "client_error",
        errors: [
          {
            code: "permission_denied",
            detail: "You cannot take ownership of more storage.",
            attr: null,
          },
        ],
      }),
    }),
  );

  const JohnRow = await getRowItem(page, "John");
  await clickOnRowItemActions(page, "John", "Move");
  const moveFolderModal = await getMoveFolderModal(page);
  const DoeRow = await getRowItem(moveFolderModal, "Doe");
  await DoeRow.click();
  await acceptMoveItem(page);

  await expect(
    page.getByText("An error occurred while moving the item."),
  ).toBeVisible();

  // The modal stays open on failure; close it and check the item stayed put.
  await moveFolderModal.getByRole("button", { name: "Cancel" }).click();
  await expect(JohnRow).toBeVisible();
});

test("Show the specific quota message when the move is rejected", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "John");
  await createFolderInCurrentFolder(page, "Doe");

  // Reject the move with the quota gate's reason code.
  await page.route("**/api/v1.0/items/*/move/", (route) =>
    route.fulfill({
      status: 403,
      contentType: "application/json",
      body: JSON.stringify({
        type: "client_error",
        errors: [
          {
            code: "user_quota_excedeed",
            detail: "You cannot take ownership of more storage.",
            attr: null,
          },
        ],
      }),
    }),
  );

  const JohnRow = await getRowItem(page, "John");
  await clickOnRowItemActions(page, "John", "Move");
  const moveFolderModal = await getMoveFolderModal(page);
  const DoeRow = await getRowItem(moveFolderModal, "Doe");
  await DoeRow.click();
  await acceptMoveItem(page);

  await expect(
    page.getByText(
      "You can no longer move documents to the root, your personal quota has been reached. Contact your administrator.",
    ),
  ).toBeVisible();

  // The modal stays open on failure; close it and check the item stayed put.
  await moveFolderModal.getByRole("button", { name: "Cancel" }).click();
  await expect(JohnRow).toBeVisible();
});

test("Search and select to move an item", async ({ page }) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  // Create the folder structure
  await createFolderInCurrentFolder(page, "John");
  await createFolderInCurrentFolder(page, "Doe");
  await navigateToFolder(page, "Doe", ["My files", "Doe"]);
  await createFolderInCurrentFolder(page, "Jane");
  await navigateToFolder(page, "Jane", ["My files", "Doe", "Jane"]);
  await createFolderInCurrentFolder(page, "Jim");

  // return to my files
  await clickToMyFiles(page);

  // Search and select to move an item
  const JohnRow = await getRowItem(page, "John");

  await expect(JohnRow).toBeVisible();
  await clickOnRowItemActions(page, "John", "Move");
  await searchAndSelectItem(page, "Jim");
  const moveFolderModal = await getMoveFolderModal(page);
  await expectExplorerBreadcrumbs(moveFolderModal, ["Doe", "Jane", "Jim"]);
  await acceptMoveItem(page);

  await clickToMyFiles(page);
  await expect(JohnRow).not.toBeVisible();
  await navigateToFolder(page, "Doe", ["My files", "Doe"]);
  await navigateToFolder(page, "Jane", ["My files", "Doe", "Jane"]);
  await navigateToFolder(page, "Jim", ["My files", "Doe", "Jane", "Jim"]);
  await expect(JohnRow).toBeVisible();
});

test("Move item to root", async ({ page }) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  // Create the folder structure
  await createFolderInCurrentFolder(page, "John");
  await navigateToFolder(page, "John", ["My files", "John"]);
  const DoeItem = await createFolderInCurrentFolder(page, "Doe");
  await clickToMyFiles(page);
  await expect(DoeItem).not.toBeVisible();
  await navigateToFolder(page, "John", ["My files", "John"]);
  await expect(DoeItem).toBeVisible();
  await clickOnRowItemActions(page, "Doe", "Move");
  await clickAndAcceptMoveToRoot(page);
  await expect(DoeItem).not.toBeVisible();
  await clickToMyFiles(page);
  await expect(DoeItem).toBeVisible();
});
