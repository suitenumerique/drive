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

// A restriction entry the user cannot access is still shown. Opening it must
// explain the denial in the preview instead of navigating into the folder.
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
    // 1. Display the denied entry on the surface under test: the parent
    //    listing (desktop or mobile), the Favorites page or the sidebar.
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
    // 2. The entry looks and behaves like an enabled item: inaccessible
    //    entries are actionable, clicking opens their explanation.
    await expect(entry).toBeVisible();
    await expect(entry).not.toHaveAttribute("aria-disabled", "true");
    await expect(entry).toHaveCSS("opacity", "1");
    // 3. Remember the URL and record any request about the hidden folder:
    //    opening the entry must neither navigate nor try to load its content.
    const url = page.url();
    const contentRequests: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes(`/items/${target.id}/`))
        contentRequests.push(request.url());
    });
    // 4. Open the entry the way each surface does: single click on mobile and
    //    in the sidebar, double click in a desktop grid.
    if (surface === "mobile" || surface === "Favorites sidebar")
      await entry.click();
    else await entry.dblclick();
    // 5. The preview opens on a no-access screen showing the folder's name,
    //    its icon and the reason, without offering to request access.
    const preview = page.getByTestId("file-preview");
    await expect(preview.locator(".file-preview-no-access")).toBeVisible();
    await expect(preview.locator("h1")).toHaveText(names.denied);
    await expect(
      preview.locator(".file-preview__title-wrapper img.c__file-icon"),
    ).toBeVisible();
    // WebKit derives an SVG's natural size from its layout, so only check that
    // the icon actually loaded.
    await expect
      .poll(() =>
        preview
          .locator(".file-preview__title-wrapper img")
          .evaluate((image: HTMLImageElement) => image.naturalWidth),
      )
      .toBeGreaterThan(0);
    await expect(preview).toContainText(
      "You do not have the necessary permissions to open this folder.",
    );
    await expect(
      preview.getByRole("button", { name: "Request access" }),
    ).toHaveCount(0);
    // 6. No file viewer is mounted, the URL is unchanged and nothing was
    //    requested about the folder.
    await expect(
      preview.locator(
        ".image-viewer, .pdf-preview, .audio-player, video, iframe",
      ),
    ).toHaveCount(0);
    await expect(page).toHaveURL(url);
    expect(contentRequests).toEqual([]);
    // 7. The preview closes with its Close button.
    await preview
      .locator(".file-preview-no-access")
      .getByRole("button", { name: "Close", exact: true })
      .click();
    await expect(preview).not.toBeVisible();
    // 8. It can be reopened and closed with Escape, still without navigating
    //    or loading anything.
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
  // 1. Open the denied entry from the parent listing: its no-access preview
  //    is displayed.
  await page.goto(itemUrl(folders.parent.id));
  await (await getRowItem(page, names.denied)).dblclick();
  const preview = page.getByTestId("file-preview");
  const next = preview.locator(".file-preview__next-button button");
  const previous = preview.locator(".file-preview__previous-button button");
  await expect(preview.locator(".file-preview-no-access")).toBeVisible();
  // 2. The parent holds exactly two previewable items, the denied entry and
  //    the document. Whichever arrow is enabled leads to the other one, so
  //    the test does not depend on the listing order.
  const forward = (await next.isEnabled()) ? next : previous;
  const backward = (await next.isEnabled()) ? previous : next;
  // 3. Step to the document: it is the end of the list, so folders the user
  //    can navigate into are not part of the preview sequence.
  await forward.click();
  await expect(preview.locator("h1")).toHaveText(names.file);
  await expect(preview.locator(".file-preview-no-access")).toHaveCount(0);
  await expect(forward).toBeDisabled();
  // 4. Step back to the denied entry, which is the other end of the list.
  await backward.click();
  await expect(preview.locator("h1")).toHaveText(names.denied);
  await expect(backward).toBeDisabled();
});

test("ordinary folders and accessible restrictions navigate to real folders; deleted targets cannot open", async ({
  page,
  folders,
}) => {
  // 1. Double clicking a plain folder or an accessible restriction entry
  //    navigates to the real folder (the entry's target) without a preview.
  for (const title of [names.normal, names.accessible]) {
    const item = findItem(folders.items, title);
    await page.goto(itemUrl(folders.parent.id));
    await (await getRowItem(page, title)).dblclick();
    await expect(page).toHaveURL(
      new RegExp(`/explorer/items/${item.target?.id ?? item.id}$`),
    );
    await expect(page.getByTestId("file-preview")).toHaveCount(0);
  }
  // 2. An entry whose target was deleted is disabled, hence the forced
  //    click: it neither navigates nor opens a preview.
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
  // 1. The API's folder filter keeps restriction entries and drops files.
  const children = `items/${folders.parent.id}/children/`;
  const folderItems = await listItems(page, `${children}?type=folder`);
  expect(findItem(folderItems, names.denied).type).toBe("restriction");
  expect(folderItems.some((item) => item.type === "file")).toBe(false);
  // 2. The move modal, which browses folders only, therefore lists the
  //    entries as possible destinations and hides the document.
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
  // 3. Filter the listing on PDF files and wait for the filtered request.
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
  // 4. The text document is filtered out, yet restriction entries remain so
  //    the user can keep browsing through them.
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
  // 1. Sign in a second user in their own browser context: the reader who
  //    only reaches the restrictable folder through the parent's accesses.
  const context = await browser.newContext();
  try {
    const reader = await context.newPage();
    await login(reader, "inherited@example.com");
    const child = findItem(folders.items, names.child);
    const search = `items/search/?title=${encodeURIComponent(names.child)}`;
    // Searches the folder by name in the reader's quick search, waiting for
    // that exact search request so stale results are never counted.
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
    // 2. While the folder is open, the reader finds it, in the API and in
    //    the search modal.
    expect(findItem(await listItems(reader, search), names.child).id).toBe(
      child.id,
    );
    await expectReaderSearch(1);
    // 3. The owner restricts the folder: it disappears from the reader's
    //    search results.
    await openSharing(page, folders, "row");
    await setRestriction(page, child.id, true);
    expect(await listItems(reader, search)).toEqual([]);
    await expectReaderSearch(0);
    // 4. The owner still finds the real folder, and search never returns
    //    restriction entries: neither for it nor for a folder they cannot
    //    access.
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
    // 5. Reopening the folder makes it searchable by the reader again.
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
  // 1. Sign in as a user whose only access to the restricted folder is its
  //    link, and record any request for its members or invitations: they
  //    would be refused, so the interface must not send them.
  const target = findItem(folders.items, names.link).target!;
  await login(page, "link-only@example.com");
  const memberRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/items\/[^/]+\/(accesses|invitations)\//.test(request.url()))
      memberRequests.push(request.url());
  });
  // 2. Open the folder by URL: its content is listed.
  await page.goto(itemUrl(target.id));
  await expect(
    await getRowItem(page, `${names.link} descendant`),
  ).toBeVisible();
  // 3. The backend grants this user neither restriction nor member viewing.
  const item = await (
    await page.request.get(`${API}/items/${target.id}/`)
  ).json();
  expect(item.abilities.restrict).toBe(false);
  expect(item.abilities.accesses_view).toBe(false);
  // 4. Accordingly the folder menu offers no Share action, and no member
  //    request was sent along the way.
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
