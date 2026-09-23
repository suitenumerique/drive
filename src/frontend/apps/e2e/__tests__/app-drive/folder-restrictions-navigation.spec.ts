import { expect } from "@playwright/test";
import { login } from "./utils-common";
import { clickOnRowItemActions, getRowItem } from "./utils-embedded-grid";
import { getItemTree, openTreeNode } from "./utils-tree";
import { getMoveFolderModal, searchAndSelectItem } from "./utils/move-utils";
import {
  API,
  findItem,
  itemUrl,
  listItems,
  names,
  openSharing,
  setRestriction,
  test,
} from "./utils/restriction-utils";

for (const surface of [
  "desktop",
  "mobile",
  "Favorites grid",
  "Favorites sidebar",
] as const) {
  test(`${surface}: denied folder opens a preview without navigating or loading content`, async ({
    page,
    folders,
  }) => {
    if (surface === "mobile")
      await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(
      surface === "Favorites grid"
        ? itemUrl("favorites")
        : itemUrl(folders.parent.id),
    );
    const target = findItem(folders.items, names.denied).target!;
    if (surface === "Favorites sidebar")
      await openTreeNode(page, "Starred", true);
    const entry =
      surface === "Favorites sidebar"
        ? (await getItemTree(page, names.denied)).getByTestId(
            "tree_item_content",
          )
        : (await getRowItem(page, names.denied)).getByRole("cell").first();
    await expect(entry).toBeVisible();
    // Inaccessible entries are actionable: clicking opens their explanation.
    await expect(entry).not.toHaveAttribute("aria-disabled", "true");
    await expect(entry).toHaveCSS("opacity", "1");
    const url = page.url();
    const contentRequests: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes(`/items/${target.id}/`))
        contentRequests.push(request.url());
    });
    if (surface === "mobile" || surface === "Favorites sidebar")
      await entry.click();
    else await entry.dblclick();
    const preview = page.getByTestId("file-preview");
    await expect(preview.locator(".file-preview-no-access")).toBeVisible();
    await expect(preview.locator("h1")).toHaveText(names.denied);
    await expect(
      preview.locator(".file-preview__title-wrapper img.c__file-icon"),
    ).toBeVisible();
    await expect(
      preview.locator(".file-preview__title-wrapper img"),
    ).toHaveJSProperty("naturalWidth", 16);
    await expect(preview).toContainText(
      "You do not have the necessary permissions to open this folder.",
    );
    await expect(
      preview.getByRole("button", { name: "Request access" }),
    ).toHaveCount(0);
    await expect(
      preview.locator(
        ".image-viewer, .pdf-preview, .audio-player, video, iframe",
      ),
    ).toHaveCount(0);
    await expect(page).toHaveURL(url);
    expect(contentRequests).toEqual([]);
    await preview
      .locator(".file-preview-no-access")
      .getByRole("button", { name: "Close", exact: true })
      .click();
    await expect(preview).not.toBeVisible();
    if (surface === "mobile" || surface === "Favorites sidebar")
      await entry.click();
    else await entry.dblclick();
    await expect(preview).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(preview).not.toBeVisible();
    await expect(page).toHaveURL(url);
    expect(contentRequests).toEqual([]);
  });
}

test("preview navigation includes a denied folder and a file, excluding navigable folders", async ({
  page,
  folders,
}) => {
  await page.goto(itemUrl(folders.parent.id));
  await (await getRowItem(page, names.denied)).dblclick();
  const preview = page.getByTestId("file-preview");
  const next = preview.locator(".file-preview__next-button button");
  const previous = preview.locator(".file-preview__previous-button button");
  await expect(preview.locator(".file-preview-no-access")).toBeVisible();
  const forward = (await next.isEnabled()) ? next : previous;
  const backward = (await next.isEnabled()) ? previous : next;
  await forward.click();
  await expect(preview.locator("h1")).toHaveText(names.file);
  await expect(preview.locator(".file-preview-no-access")).toHaveCount(0);
  await expect(forward).toBeDisabled();
  await backward.click();
  await expect(preview.locator("h1")).toHaveText(names.denied);
  await expect(backward).toBeDisabled();
});

test("ordinary folders and accessible restrictions navigate to real folders; deleted targets cannot open", async ({
  page,
  folders,
}) => {
  for (const title of [names.normal, names.accessible]) {
    const item = findItem(folders.items, title);
    await page.goto(itemUrl(folders.parent.id));
    await (await getRowItem(page, title)).dblclick();
    await expect(page).toHaveURL(
      new RegExp(`/explorer/items/${item.target?.id ?? item.id}$`),
    );
    await expect(page.getByTestId("file-preview")).toHaveCount(0);
  }
  await page.goto(itemUrl(folders.parent.id));
  const url = page.url();
  await (await getRowItem(page, names.deleted)).dblclick({ force: true });
  await expect(page).toHaveURL(url);
  await expect(page.getByTestId("file-preview")).toHaveCount(0);
});

test("folder-only navigation and file-category filters retain restriction entries", async ({
  page,
  folders,
}) => {
  const children = `items/${folders.parent.id}/children/`;
  const folderItems = await listItems(page, `${children}?type=folder`);
  expect(findItem(folderItems, names.denied).type).toBe("restriction");
  expect(folderItems.some((item) => item.type === "file")).toBe(false);
  await page.goto(itemUrl(folders.parent.id));
  await clickOnRowItemActions(page, "Movable one", "Move");
  const moveModal = await getMoveFolderModal(page);
  await searchAndSelectItem(page, names.parent);
  await expect(await getRowItem(moveModal, names.denied)).toBeVisible();
  await expect(await getRowItem(moveModal, names.accessible)).toBeVisible();
  await expect(
    moveModal.getByRole("row", { name: new RegExp(names.file) }),
  ).toHaveCount(0);
  await moveModal.getByRole("button", { name: "Cancel", exact: true }).click();
  await page
    .locator(".explorer__filters")
    .getByRole("button", { name: /^Type/ })
    .click();
  const response = page.waitForResponse(
    (result) =>
      result.url().includes(`${children}?`) &&
      result.url().includes("category=pdf"),
  );
  await page.getByRole("option", { name: "PDF", exact: true }).click();
  expect((await response).ok()).toBe(true);
  await expect(
    page.getByRole("row", { name: new RegExp(names.file) }),
  ).toHaveCount(0);
  await expect(await getRowItem(page, names.denied)).toBeVisible();
  await expect(await getRowItem(page, names.accessible)).toBeVisible();
});

test("search follows effective access and excludes restriction entries", async ({
  page,
  browser,
  folders,
}) => {
  const context = await browser.newContext();
  try {
    const reader = await context.newPage();
    await login(reader, "inherited@example.com");
    const child = findItem(folders.items, names.child);
    const search = `items/search/?title=${encodeURIComponent(names.child)}`;
    const expectReaderSearch = async (count: number) => {
      await reader.goto(itemUrl(folders.parent.id));
      await reader.getByRole("button", { name: "Search", exact: true }).click();
      const results = reader.waitForResponse((response) => {
        const url = new URL(response.url());
        return (
          url.pathname.endsWith("/items/search/") &&
          url.searchParams.get("title") === names.child
        );
      });
      await reader
        .getByRole("combobox", { name: "Quick search input" })
        .fill(names.child);
      expect((await results).ok()).toBe(true);
      await expect(
        reader.getByTestId("search-item").filter({ hasText: names.child }),
      ).toHaveCount(count);
    };
    expect(findItem(await listItems(reader, search), names.child).id).toBe(
      child.id,
    );
    await expectReaderSearch(1);
    await openSharing(page, folders, "row");
    await setRestriction(page, child.id, true);
    expect(await listItems(reader, search)).toEqual([]);
    await expectReaderSearch(0);
    const ownerResults = await listItems(page, search);
    expect(findItem(ownerResults, names.child).id).toBe(child.id);
    expect(ownerResults.every((item) => item.type !== "restriction")).toBe(
      true,
    );
    expect(
      await listItems(
        page,
        `items/search/?title=${encodeURIComponent(names.denied)}`,
      ),
    ).toEqual([]);
    await setRestriction(page, child.id, false);
    expect(findItem(await listItems(reader, search), names.child).id).toBe(
      child.id,
    );
    await expectReaderSearch(1);
  } finally {
    await context.close();
  }
});

test("link-only access opens a target without requesting members or invitations", async ({
  page,
  folders,
}) => {
  const target = findItem(folders.items, names.link).target!;
  await login(page, "link-only@example.com");
  const memberRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/items\/[^/]+\/(accesses|invitations)\//.test(request.url()))
      memberRequests.push(request.url());
  });
  await page.goto(itemUrl(target.id));
  await expect(
    await getRowItem(page, `${names.link} descendant`),
  ).toBeVisible();
  const item = await (
    await page.request.get(`${API}/items/${target.id}/`)
  ).json();
  expect(item.abilities.restrict).toBe(false);
  expect(item.abilities.accesses_view).toBe(false);
  await page
    .getByTestId("explorer-breadcrumbs")
    .getByTestId("breadcrumb-button")
    .last()
    .click();
  await expect(page.getByRole("menu")).toBeVisible();
  await expect(
    page.getByRole("menuitem", { name: "Share", exact: true }),
  ).toHaveCount(0);
  expect(memberRequests).toEqual([]);
});
