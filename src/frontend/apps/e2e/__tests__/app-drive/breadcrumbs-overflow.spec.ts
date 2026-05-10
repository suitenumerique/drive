import test, { expect, Page } from "@playwright/test";

import { clearDb, login } from "./utils-common";
import { createFolderInCurrentFolder } from "./utils-item";
import { getRowItem } from "./utils-embedded-grid";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import { clickToMyFiles } from "./utils-navigate";

// Navigate into a folder without asserting the breadcrumb chain. The shared
// `navigateToFolder` helper calls `expectExplorerBreadcrumbs`, which expects
// every chain item to be a visible button — but with names long enough to
// saturate the breadcrumb-button max-width, the collapse logic kicks in
// mid-setup and breaks that count assertion.
const dblClickIntoFolder = async (page: Page, folderName: string) => {
  const previousUrl = page.url();
  const folderRow = await getRowItem(page, folderName);
  await folderRow.dblclick();
  await page.waitForURL((url) => url.toString() !== previousUrl);
};

// Names long enough to saturate the c__breadcrumbs__button max-width (320px),
// so the chain reliably overflows the breadcrumbs container at the narrow
// test viewport.
const longFolderNames = [
  "A Really Really Quite Extremely Long Folder Name Number 1",
  "A Really Really Quite Extremely Long Folder Name Number 2",
  "A Really Really Quite Extremely Long Folder Name Number 3",
  "A Really Really Quite Extremely Long Folder Name Number 4",
];

const setupDeepFolderTree = async (page: Page) => {
  await clearDb();
  await login(page, "drive@example.com");
  // Stay in the desktop layout: the app collapses the sidebar behind a
  // hamburger below ~1024px, and switching back and forth between layouts
  // mid-test would hide the breadcrumbs entirely. At 1280 the sidebar
  // (~250px) plus the right panel (~300px) already squeeze the breadcrumbs
  // container down to ~630px, which is narrower than our chain of long
  // folder names — so the collapse logic triggers naturally without ever
  // touching the viewport again.
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await clickToMyFiles(page);

  for (const name of longFolderNames) {
    await createFolderInCurrentFolder(page, name);
    await dblClickIntoFolder(page, name);
  }
};

test("breadcrumbs collapse middle items into an ellipsis when the container is too narrow", async ({
  page,
}) => {
  await setupDeepFolderTree(page);

  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  const ellipsis = breadcrumbs.getByTestId("breadcrumb-ellipsis");
  await expect(ellipsis).toBeVisible();

  // Root and the leaf must always remain visible.
  await expect(breadcrumbs.getByTestId("default-route-button")).toBeVisible();
  const lastDynamic = breadcrumbs.getByTestId("breadcrumb-button").last();
  await expect(lastDynamic).toContainText(
    longFolderNames[longFolderNames.length - 1],
  );

  // At least one middle item should be collapsed into the ellipsis — i.e.
  // not present as a button in the visible breadcrumbs container.
  await expect(
    breadcrumbs.getByRole("button", { name: longFolderNames[0] }),
  ).toHaveCount(0);
});

test("clicking the ellipsis opens a dropdown listing the collapsed items", async ({
  page,
}) => {
  await setupDeepFolderTree(page);

  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  const ellipsis = breadcrumbs.getByTestId("breadcrumb-ellipsis");
  await expect(ellipsis).toBeVisible();
  await ellipsis.click();

  // The first long folder is the deepest hidden ancestor and should be in
  // the dropdown.
  await expect(
    page.getByRole("menuitem", { name: longFolderNames[0] }),
  ).toBeVisible();
});

test("selecting a collapsed item from the dropdown navigates to that folder", async ({
  page,
}) => {
  await setupDeepFolderTree(page);

  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  await breadcrumbs.getByTestId("breadcrumb-ellipsis").click();
  await page
    .getByRole("menuitem", { name: longFolderNames[0] })
    .click();

  await expectExplorerBreadcrumbs(page, ["My files", longFolderNames[0]]);
});
