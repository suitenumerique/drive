import test, { expect } from "@playwright/test";

import { clearDb, login } from "./utils-common";
import { createFolderInCurrentFolder } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";

test("breadcrumbs keep previous chain visible while new breadcrumb fetch is in flight", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  // Build "My files > L1 > L2 > L3" by walking down through the UI.
  await createFolderInCurrentFolder(page, "L1");
  await navigateToFolder(page, "L1", ["My files", "L1"]);
  await createFolderInCurrentFolder(page, "L2");
  await navigateToFolder(page, "L2", ["My files", "L1", "L2"]);
  await createFolderInCurrentFolder(page, "L3");
  await navigateToFolder(page, "L3", ["My files", "L1", "L2", "L3"]);

  // Reload on L3 to drop the in-memory react-query cache. After the reload
  // only L3's breadcrumb is fetched and cached — L1 / L2 are uncached, so
  // navigating to one of them later triggers a real network fetch we can
  // intercept.
  const l3Url = page.url();
  await page.goto(l3Url, { waitUntil: "domcontentloaded" });
  await expectExplorerBreadcrumbs(page, ["My files", "L1", "L2", "L3"]);

  // Block subsequent breadcrumb responses on a promise we control.
  let release!: () => void;
  const blocker = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1.0/items/*/breadcrumb/", async (route) => {
    await blocker;
    await route.continue();
  });

  // Click "L1" in the breadcrumb. URL changes and a fresh breadcrumb fetch is
  // triggered, but it is held back by our route handler.
  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  await breadcrumbs.getByTestId("breadcrumb-button").first().click();
  await page.waitForURL(/\/explorer\/items\/[^/]+/);

  // While the request is paused, the committed snapshot must remain visible.
  // The empty-middle bug would render ["My files", "L1"] here.
  await expectExplorerBreadcrumbs(page, ["My files", "L1", "L2", "L3"]);

  // Unblock and assert the atomic swap to L1's chain.
  release();
  await expectExplorerBreadcrumbs(page, ["My files", "L1"]);
  await expect(
    breadcrumbs.getByTestId("breadcrumb-button"),
  ).toHaveCount(1);
});
