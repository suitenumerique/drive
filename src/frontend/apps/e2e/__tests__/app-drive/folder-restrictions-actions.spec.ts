import { expect, Page } from "@playwright/test";
import { login } from "./utils-common";
import { getRowItem, getRowItemActions } from "./utils-embedded-grid";
import {
  confirmation,
  findItem,
  itemUrl,
  names,
  openSharing,
  shareModal,
  test,
} from "./utils/restriction-utils";

const openRowMenu = async (page: Page, title: string) => {
  await (await getRowItemActions(page, title)).click({ force: true });
  await expect(page.getByRole("menu")).toBeVisible();
};

const menuItem = (page: Page, name: string) =>
  page.getByRole("menuitem", { name, exact: true });

// A restriction entry stands for its folder: from the parent listing, its menu
// must offer the folder actions its breadcrumb offers, following the user's
// permissions on the folder rather than on the entry.
test("restriction entries offer the actions their folder allows", async ({
  page,
  folders,
}) => {
  await page.goto(itemUrl(folders.parent.id));

  // 1. The owner of a restricted folder can download and rename it from the
  //    parent listing, like any other folder they own.
  await openRowMenu(page, names.accessible);
  for (const action of ["Share", "Download", "Rename"])
    await expect(menuItem(page, action)).toBeVisible();
  await page.keyboard.press("Escape");

  // 2. A parent owner who is only reader on the restricted folder can share
  //    (view members) and download it, but not rename it.
  await openRowMenu(page, names.readOnly);
  for (const action of ["Share", "Download"])
    await expect(menuItem(page, action)).toBeVisible();
  await expect(menuItem(page, "Rename")).toHaveCount(0);
  await page.keyboard.press("Escape");

  // 3. Downloading exports the folder itself, not the restriction entry.
  const readOnly = findItem(folders.items, names.readOnly);
  const exportRequest = page.waitForRequest((request) =>
    request.url().includes(`/items/${readOnly.target!.id}/export/`),
  );
  await openRowMenu(page, names.readOnly);
  await menuItem(page, "Download").click();
  await exportRequest;
});

test("renaming a restriction entry renames its folder", async ({
  page,
  folders,
}) => {
  const accessible = findItem(folders.items, names.accessible);
  await page.goto(itemUrl(folders.parent.id));

  // 1. Rename the entry from its row menu; the request must target the folder,
  //    since the entry only mirrors the folder's title.
  await openRowMenu(page, names.accessible);
  await menuItem(page, "Rename").click();
  const input = page.getByRole("textbox");
  await input.fill("Renamed restricted");
  const renameResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/items/${accessible.target!.id}/`) &&
      response.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "Rename", exact: true }).click();
  expect((await renameResponse).ok()).toBeTruthy();

  // 2. The listing shows the new title without a reload.
  await getRowItem(page, "Renamed restricted");
  await expect(page.getByRole("row", { name: names.accessible })).toHaveCount(
    0,
  );
});

test("breadcrumbs mark restricted folders", async ({ page, folders }) => {
  const accessible = findItem(folders.items, names.accessible);
  const restrictedIcon = (page: Page) =>
    page.getByRole("img", { name: "Restricted access", exact: true });

  // 1. Inside the restricted folder, the current breadcrumb item is marked.
  await page.goto(itemUrl(accessible.target!.id));
  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  const buttons = breadcrumbs.getByTestId("breadcrumb-button");
  await expect(buttons.last()).toContainText(names.accessible);
  await expect(restrictedIcon(page)).toHaveCount(1);
  await expect(buttons.last().getByRole("img")).toHaveAccessibleName(
    "Restricted access",
  );

  // 2. One level deeper, the mark stays on the restricted ancestor only.
  await (await getRowItem(page, "Cycle descendant")).dblclick();
  await expect(buttons.last()).toContainText("Cycle descendant");
  await expect(restrictedIcon(page)).toHaveCount(1);
  await expect(
    buttons.filter({ hasText: names.accessible }).getByRole("img"),
  ).toHaveAccessibleName("Restricted access");

  // 3. An ordinary folder has no mark.
  await page.goto(itemUrl(findItem(folders.items, names.normal).id));
  await expect(buttons.last()).toContainText(names.normal);
  await expect(restrictedIcon(page)).toHaveCount(0);

  // 4. On mobile, the current restricted folder is marked as well.
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto(itemUrl(accessible.target!.id));
  await expect(
    page
      .locator(".explorer__content__breadcrumbs--mobile")
      .getByRole("img", { name: "Restricted access", exact: true }),
  ).toBeVisible();

  // 5. A user invited directly on a restricted folder, without access to its
  //    parent, has it as the only breadcrumb item: the mobile root layout
  //    must mark it too.
  const readOnly = findItem(folders.items, names.readOnly);
  await login(page, "other-owner@example.com");
  await page.goto(itemUrl(readOnly.target!.id));
  const mobileRoot = page.locator(
    ".explorer__content__breadcrumbs--mobile__workspace",
  );
  await expect(mobileRoot).toContainText(names.readOnly);
  await expect(
    mobileRoot.getByRole("img", { name: "Restricted access", exact: true }),
  ).toBeVisible();
});

// The ui-kit copy speaks of items: Drive names them folders, since only
// folders can be restricted.
test("restriction copy speaks of folders", async ({ page, folders }) => {
  // 1. Open sharing on a plain folder; its menu offers to restrict it, with
  //    the folder wording.
  await openSharing(page, folders, "row");
  await shareModal(page)
    .getByRole("button", { name: "More actions", exact: true })
    .click();
  const restrict = page.getByRole("menuitem", { name: /Restrict access/ });
  await expect(restrict).toContainText(
    "Only people added specifically to this folder will have access",
  );

  // 2. The confirmation states the consequence for the parent folder in bold,
  //    then what happens to people added to the folder.
  await restrict.click();
  await expect(confirmation(page).locator("strong")).toHaveText(
    "Access inherited from the parent folder will be removed.",
  );
  await expect(confirmation(page)).toContainText(
    "People added directly to this folder will keep their access.",
  );
});
