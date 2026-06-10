import test, { expect } from "@playwright/test";
import { clearDb, login, runFixture } from "./utils-common";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  expectRowItem,
  expectRowItemIsNotVisible,
} from "./utils-embedded-grid";
import {
  closeShareModal,
  openShareModal,
  selectLinkReach,
} from "./utils/share-utils";

test("Filter items by file type category", async ({ page }) => {
  await clearDb();

  await runFixture("e2e_fixture_filters");
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);
  await expectRowItem(page, "Quarterly report");

  const filtersBar = page.locator(".explorer__filters");

  await filtersBar.getByRole("button", { name: /^Type/ }).click();
  await page.getByRole("option", { name: "PDF" }).click();

  await expectRowItem(page, "Filters folder");
  await expectRowItem(page, "Quarterly report");
  await expectRowItem(page, "Shared report");
  await expectRowItemIsNotVisible(page, "Holiday photo");

  await filtersBar.getByRole("button", { name: /^Type/ }).click();
  await page.getByRole("option", { name: "Image" }).click();

  await expectRowItem(page, "Filters folder");
  await expectRowItem(page, "Holiday photo");
  await expectRowItemIsNotVisible(page, "Quarterly report");

  await filtersBar.getByRole("button", { name: /^Type/ }).click();
  await page.getByRole("option", { name: "Reset" }).click();

  await expectRowItem(page, "Quarterly report");
  await expectRowItem(page, "Holiday photo");
});

test("Filter items by shared contact", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);
  await expectRowItem(page, "Quarterly report");

  const filtersBar = page.locator(".explorer__filters");

  // Frequent contacts are suggested without typing anything.
  await filtersBar.getByRole("button", { name: /^Shared with/ }).click();
  await page.getByRole("option", { name: /Alice Doe/ }).click();

  await expectRowItem(page, "Shared report");
  await expectRowItemIsNotVisible(page, "Quarterly report");
  await expectRowItemIsNotVisible(page, "Filters folder");

  await filtersBar.getByRole("button", { name: /^Shared with/ }).click();
  await page.getByRole("option", { name: "Reset" }).click();

  await expectRowItem(page, "Quarterly report");
  await expectRowItem(page, "Filters folder");
});

test("Filter items by modification date", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);
  await expectRowItem(page, "Old report");

  const filtersBar = page.locator(".explorer__filters");

  await filtersBar.getByRole("button", { name: /^Modified/ }).click();
  await page.getByRole("option", { name: "Today" }).click();

  await expectRowItem(page, "Quarterly report");
  await expectRowItemIsNotVisible(page, "Old report");

  await filtersBar.getByRole("button", { name: /^Modified/ }).click();
  await page.getByRole("option", { name: "Reset" }).click();

  await expectRowItem(page, "Old report");
});

test("Public folder — anonymous visitor sees filters without the contact filter", async ({
  page,
  browser,
}) => {
  await clearDb();
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);

  await createFolderInCurrentFolder(page, "Public folder");
  await navigateToFolder(page, "Public folder", ["My files", "Public folder"]);
  await openShareModal(page);
  await selectLinkReach(page, "Public");
  await closeShareModal(page);
  const folderUrl = page.url();

  const anonContext = await browser.newContext();
  const anonPage = await anonContext.newPage();
  await anonPage.goto(folderUrl);

  const filtersBar = anonPage.locator(".explorer__filters");
  await expect(filtersBar.getByRole("button", { name: /^Type/ })).toBeVisible();
  await expect(
    filtersBar.getByRole("button", { name: /^Modified/ }),
  ).toBeVisible();
  // The contact filter requires authentication: its contacts request would
  // get a 401 and redirect the anonymous visitor to the 401 page.
  await expect(
    filtersBar.getByRole("button", { name: /^Shared with/ }),
  ).not.toBeVisible();
  expect(anonPage.url()).toBe(folderUrl);

  await anonContext.close();
});
