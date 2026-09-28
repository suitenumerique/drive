import test, {
  test as base,
  BrowserContext,
  expect,
  Page,
} from "@playwright/test";
import { clearDb, login } from "./utils-common";
import {
  clickToFavorites,
  clickToMyFiles,
  clickToRecent,
  clickToSharedWithMe,
  navigateToFolder,
} from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import { shareCurrentItemWithWebkitUser } from "./utils/share-utils";
import { expectRowItem } from "./utils-embedded-grid";
import { expectExplorerBreadcrumbs } from "./utils-explorer";

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

const READ_ONLY_FOLDER = "ReadOnly folder";

const setupReadOnlyFolderSharedWithWebkitUser = async (
  userA: Page,
  userB: Page,
) => {
  await clearDb();
  await login(userA, "drive@example.com");
  await login(userB, "user@webkit.test");

  await userA.goto("/");
  await clickToMyFiles(userA);
  await createFolderInCurrentFolder(userA, READ_ONLY_FOLDER);
  await navigateToFolder(userA, READ_ONLY_FOLDER, [
    "My files",
    READ_ONLY_FOLDER,
  ]);
  await shareCurrentItemWithWebkitUser(userA, "Reader");
};

const navigateIntoReadOnlyFolder = async (page: Page) => {
  await page.goto("/");
  await clickToSharedWithMe(page);
  await navigateToFolder(page, READ_ONLY_FOLDER, [
    "Shared with me",
    READ_ONLY_FOLDER,
  ]);
};

const createViaNewMenu = async (
  page: Page,
  opts: { menuItem: string; inputLabel: string; name: string },
) => {
  await page.getByRole("button", { name: "New" }).click();
  await page.getByRole("menuitem", { name: opts.menuItem }).click();
  await page.getByRole("textbox", { name: opts.inputLabel }).fill(opts.name);
  await page.getByRole("button", { name: "Create" }).click();
};

const createFolderViaNewMenu = (page: Page, folderName: string) =>
  createViaNewMenu(page, {
    menuItem: "New folder",
    inputLabel: "Folder name",
    name: folderName,
  });

const createDocumentViaNewMenu = (page: Page, fileName: string) =>
  createViaNewMenu(page, {
    menuItem: "New text document",
    inputLabel: "File name",
    name: fileName,
  });

MultiUserTest(
  "+ New > Folder from a read-only folder falls back to My files",
  async ({ userA, userB }) => {
    await setupReadOnlyFolderSharedWithWebkitUser(userA.page, userB.page);

    await navigateIntoReadOnlyFolder(userB.page);

    // The + New menu must still be populated even though the folder is read-only
    await createFolderViaNewMenu(userB.page, "Fallback folder");

    // The folder is created in B's own My files, and we are redirected into it
    await expectExplorerBreadcrumbs(userB.page, [
      "My files",
      "Fallback folder",
    ]);
    await expect(userB.page).toHaveURL(/\/explorer\/items\/[0-9a-f-]+$/);

    // And it is visible in the My files listing
    await clickToMyFiles(userB.page);
    await expectRowItem(userB.page, "Fallback folder");
  },
);

MultiUserTest(
  "+ New > Document from a read-only folder falls back to the My files view",
  async ({ userA, userB }) => {
    await setupReadOnlyFolderSharedWithWebkitUser(userA.page, userB.page);

    await navigateIntoReadOnlyFolder(userB.page);

    await createDocumentViaNewMenu(userB.page, "Fallback doc");

    // For a file we land on the My files view (the file itself is not navigable)
    await expect(userB.page).toHaveURL(/\/explorer\/items\/my-files$/);
    await expectExplorerBreadcrumbs(userB.page, ["My files"]);
    await expectRowItem(userB.page, "Fallback doc");
  },
);

const virtualTabs: Array<{
  go: (page: Page) => Promise<void>;
  label: string;
}> = [
  { go: clickToRecent, label: "Recent" },
  { go: clickToSharedWithMe, label: "Shared" },
  { go: clickToFavorites, label: "Starred" },
];

for (const { go, label } of virtualTabs) {
  test(`+ New from ${label} tab creates in My files`, async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await go(page);

    const folderName = `Tab folder ${label}`;
    await createFolderViaNewMenu(page, folderName);

    // Created in My files (no parent), and we are redirected into it
    await expectExplorerBreadcrumbs(page, ["My files", folderName]);
  });
}

test("+ New inside a writable folder still creates in place", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  await createFolderInCurrentFolder(page, "Writable parent");
  await navigateToFolder(page, "Writable parent", [
    "My files",
    "Writable parent",
  ]);

  // Use the + New dropdown directly to make sure it also works in place
  await createFolderViaNewMenu(page, "Child");

  // Still inside the parent — no fallback redirect to My files
  await expectExplorerBreadcrumbs(page, ["My files", "Writable parent"]);
  await expectRowItem(page, "Child");
});
