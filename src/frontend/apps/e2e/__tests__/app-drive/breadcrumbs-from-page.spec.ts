import { clearDb, login } from "./utils-common";
import { expect } from "@playwright/test";
import test from "@playwright/test";
import { createFolderInCurrentFolder } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";

test("Check that the from page is not displayed when the user paste a new url in the browser", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "Bar");
  await createFolderInCurrentFolder(page, "Foo");

  await navigateToFolder(page, "Foo", ["My files", "Foo"]);
  const fooUrl = page.url();

  await clickToMyFiles(page);
  await navigateToFolder(page, "Bar", ["My files", "Bar"]);
  await page.goto(fooUrl);
  await expect(page.getByTestId("default-route-button")).not.toBeVisible();
  await expectExplorerBreadcrumbs(page, ["Foo"]);
});
