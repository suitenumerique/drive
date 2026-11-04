import { expect, Page } from "@playwright/test";
import { getRowItem, getRowItemActions } from "./utils-embedded-grid";
import { findItem, itemUrl, names, test } from "./utils/restriction-utils";

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
