import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import {
  createFolderInCurrentFolder,
  createFileFromTemplate,
} from "./utils-item";
import { clickToMyFiles, clickToTrash } from "./utils-navigate";
import {
  clickOnRowItemActions,
  expectRowItem,
  expectRowItemIsNotVisible,
  getRowItem,
} from "./utils-embedded-grid";

test("Checks that hard deleting an item from the trash refreshes the list", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  const folderName = "Folder to hard delete";
  await createFolderInCurrentFolder(page, folderName);
  await clickOnRowItemActions(page, folderName, "Delete");

  await clickToTrash(page);
  await expectRowItem(page, folderName);

  // Trash actions cell uses a different button structure than the regular grid
  const row = await getRowItem(page, folderName);
  await row.getByRole("button").last().click();
  await page.getByRole("menuitem", { name: "Delete forever" }).click();
  await page.getByRole("button", { name: "Delete forever" }).click();

  await expectRowItemIsNotVisible(page, folderName);
});

test("Checks that hard deleting an item from the trash via the selection bar refreshes the list", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  const folderName = "Folder to hard delete from bar";
  await createFolderInCurrentFolder(page, folderName);
  await clickOnRowItemActions(page, folderName, "Delete");

  await clickToTrash(page);
  await expectRowItem(page, folderName);

  // Click on the row to select the item and reveal the selection bar
  const row = await getRowItem(page, folderName);
  await row.click();
  await expect(page.getByText("1 item selected")).toBeVisible();

  // Click "Delete forever" from the selection bar
  await page
    .locator(".explorer__selection-bar")
    .getByRole("button", { name: "Delete forever" })
    .click();
  await page.getByRole("button", { name: "Delete forever" }).click();

  await expectRowItemIsNotVisible(page, folderName);
});

test("Checks that double-clicking a deleted folder in the trash shows a folder message", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  const folderName = "Folder in trash";
  await createFolderInCurrentFolder(page, folderName);
  await clickOnRowItemActions(page, folderName, "Delete");

  await clickToTrash(page);
  const row = await getRowItem(page, folderName);
  await row
    .getByRole("button", { name: folderName })
    .first()
    .dblclick({ force: true });

  await expect(page.getByText("This folder is in the trash")).toBeVisible();
  await expect(
    page.getByText("To display this folder, you need to restore it first."),
  ).toBeVisible();

  // Dismiss the modal and verify we're still on the trash page
  await page.getByRole("button", { name: "Ok" }).click();
  expect(page.url()).toContain("/explorer/trash");
});

test("Checks that double-clicking a deleted file in the trash shows a file message", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  const fileName = "File in trash";
  await createFileFromTemplate(page, fileName);
  await clickOnRowItemActions(page, fileName, "Delete");

  await clickToTrash(page);
  const row = await getRowItem(page, fileName);
  await row
    .getByRole("button", { name: fileName })
    .first()
    .dblclick({ force: true });

  await expect(page.getByText("This file is in the trash")).toBeVisible();
  await expect(
    page.getByText("To display this file, you need to restore it first."),
  ).toBeVisible();

  // Dismiss the modal and verify we're still on the trash page
  await page.getByRole("button", { name: "Ok" }).click();
  expect(page.url()).toContain("/explorer/trash");
});
