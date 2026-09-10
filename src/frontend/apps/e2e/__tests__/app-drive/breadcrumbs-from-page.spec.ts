import { clearDb, login } from "./utils-common";
import { expect } from "@playwright/test";
import test from "@playwright/test";
import { createFolderInCurrentFolder } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import {
  clickToFavorites,
  clickToMyFiles,
  navigateToFolder,
} from "./utils-navigate";
import { starItem } from "./utils/starred-utils";

test("Check that the from page is guessed when the user paste a new url in the browser", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@drive.world");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "Bar");

  await createFolderInCurrentFolder(page, "Foo");

  await navigateToFolder(page, "Foo", ["My files", "Foo"]);
  const fooUrl = page.url();

  await clickToMyFiles(page);
  await navigateToFolder(page, "Bar", ["My files", "Bar"]);
  await page.goto(fooUrl, { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("default-route-button")).not.toBeVisible();
  await expectExplorerBreadcrumbs(page, ["My files", "Foo"]);
});

test("Check that the from page is guessed when the user paste a new url and was browsing favorites", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@drive.world");
  await page.goto("/");

  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "Bar");
  await navigateToFolder(page, "Bar", ["My files", "Bar"]);
  const barUrl = page.url();
  await createFolderInCurrentFolder(page, "Sub Bar");

  await clickToMyFiles(page);

  await createFolderInCurrentFolder(page, "Foo");
  await starItem(page, "Foo");

  await clickToFavorites(page);
  await page.reload();
  await navigateToFolder(page, "Foo", ["Starred", "Foo"]);

  await page.goto(barUrl, { waitUntil: "domcontentloaded" });

  await expectExplorerBreadcrumbs(page, ["My files", "Bar"]);
  await navigateToFolder(page, "Sub Bar", ["My files", "Bar", "Sub Bar"]);
  await expectExplorerBreadcrumbs(page, ["My files", "Bar", "Sub Bar"]);
});
