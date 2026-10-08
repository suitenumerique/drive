import { expect } from "@playwright/test";
import { login } from "./utils-common";
import { clickOnRowItemActions } from "./utils-embedded-grid";
import { openTreeNode } from "./utils-tree";
import {
  API,
  askRestriction,
  confirmation,
  entryPoints,
  expectParentEntry,
  findItem,
  itemUrl,
  listItems,
  names,
  openSharing,
  setRestriction,
  shareModal,
  test,
} from "./utils/restriction-utils";

// Restricting swaps the folder for a restriction entry in its parent, which
// refreshes the surface the share modal was opened from. The modal must
// survive that refresh wherever it was opened.
for (const entryPoint of entryPoints) {
  test(`${entryPoint}: restrict and reopen without remounting sharing`, async ({
    page,
    folders,
  }) => {
    // 1. Open the folder's share modal from the entry point. Keep a handle
    //    on its DOM node to later prove it is the same modal, not a new one.
    //    The reader inheriting access from the parent is listed.
    const child = findItem(folders.items, names.child);
    await openSharing(page, folders, entryPoint);
    const originalModal = await shareModal(page).elementHandle();
    const members = shareModal(page).getByTestId("members-list");
    await expect(members).toContainText("Inherited Reader");
    // 2. Restrict the folder: the very same modal is still mounted.
    await setRestriction(page, child.id, true);
    expect(
      await originalModal!.evaluate((element) => element.isConnected),
    ).toBe(true);
    // 3. The parent now lists a restriction entry instead of the folder. In
    //    listings, the folder's row is replaced by the entry's row and the
    //    selection is cleared.
    const restrictedEntry = await expectParentEntry(page, folders, true);
    await expect(page.locator("tr.selected")).toHaveCount(0);
    if (!entryPoint.includes("breadcrumb")) {
      await expect(page.locator(`tr[data-id="${child.id}"]`)).toHaveCount(0);
      await expect(
        page.locator(`tr[data-id="${restrictedEntry.id}"]`),
      ).toBeVisible();
    }
    // 4. Members inherited from the parent are gone; the editor granted on
    //    the folder itself keeps their role.
    await expect(members).not.toContainText("Inherited Reader");
    await expect(
      members
        .getByTestId("share-member-item")
        .filter({ hasText: "Direct Editor" }),
    ).toContainText("Editor");
    // 5. Surface specifics: the right panel closes since its item left the
    //    listing, while inside the folder the user stays in place and the
    //    breadcrumb still leads back to the parent.
    if (entryPoint === "right panel")
      await expect(page.getByTestId("right-panel")).not.toBeVisible();
    if (entryPoint.includes("breadcrumb")) {
      await expect(page).toHaveURL(new RegExp(child.id));
      const breadcrumbs =
        entryPoint === "breadcrumb"
          ? page.getByTestId("explorer-breadcrumbs")
          : page.locator(".explorer__content__breadcrumbs--mobile");
      await expect(breadcrumbs).toContainText(names.parent);
    }
    // 6. Reopen access from the same modal: everything is restored. The
    //    parent lists the folder again, the inherited reader is back and
    //    the direct editor is untouched.
    await setRestriction(page, child.id, false);
    expect(
      await originalModal!.evaluate((element) => element.isConnected),
    ).toBe(true);
    await expectParentEntry(page, folders, false);
    if (!entryPoint.includes("breadcrumb")) {
      await expect(page.locator(`tr[data-id="${child.id}"]`)).toBeVisible();
      await expect(
        page.locator(`tr[data-id="${restrictedEntry.id}"]`),
      ).toHaveCount(0);
    }
    await expect(members).toContainText("Inherited Reader");
    await expect(
      members
        .getByTestId("share-member-item")
        .filter({ hasText: "Direct Editor" }),
    ).toContainText("Editor");
    if (entryPoint === "breadcrumb")
      await expect(page.getByTestId("explorer-breadcrumbs")).toContainText(
        names.parent,
      );
  });
}

test("sharing opened from a restriction entry uses the target folder endpoint", async ({
  page,
  folders,
}) => {
  // 1. Open sharing from the row of an already restricted folder, which is
  //    a restriction entry, and record the restriction requests.
  const entry = findItem(folders.items, names.accessible);
  await openSharing(page, folders, "row", names.accessible);
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/restrict/")) requests.push(request.url());
  });
  // 2. Reopen then restrict it again.
  await setRestriction(page, entry.target!.id, false);
  await setRestriction(page, entry.target!.id, true);
  // 3. Both requests addressed the real folder, never the entry's own id.
  expect(requests).toHaveLength(2);
  expect(
    requests.every((url) => url.endsWith(`/${entry.target!.id}/restrict/`)),
  ).toBe(true);
});

for (const restrict of [true, false]) {
  test(`${restrict ? "Restrict" : "Open"}: Cancel, Close and Escape leave access unchanged`, async ({
    page,
    folders,
  }) => {
    // 1. Open sharing on a folder in the opposite state: an open folder to
    //    try restricting, a restricted one to try reopening. Record the
    //    restriction requests, as none may be sent.
    const title = restrict ? names.child : names.accessible;
    const item = findItem(folders.items, title);
    await openSharing(page, folders, "row", title);
    const requests: string[] = [];
    page.on("request", (request) => {
      if (request.url().endsWith("/restrict/")) requests.push(request.method());
    });
    for (const action of ["Cancel", "close", "Escape"]) {
      // 2. Ask for the change, then back out with each way of dismissing
      //    the confirmation.
      await askRestriction(page, restrict);
      if (action === "Escape") await page.keyboard.press("Escape");
      else
        await confirmation(page)
          .getByRole("button", { name: action, exact: true })
          .click();
      // 3. Only the confirmation closes: sharing stays open and the backend
      //    still reports the original state.
      await expect(confirmation(page)).not.toBeVisible();
      await expect(shareModal(page)).toBeVisible();
      const response = await page.request.get(
        `${API}/items/${item.target?.id ?? item.id}/`,
      );
      expect(response.ok()).toBe(true);
      expect((await response.json()).is_restricted).toBe(!restrict);
    }
    expect(requests).toEqual([]);
  });
}

for (const method of ["POST", "DELETE"] as const) {
  test(`${method} failure keeps sharing open and allows retry`, async ({
    page,
    folders,
  }) => {
    // 1. Open sharing. To test a failing reopen (DELETE), the folder must be
    //    restricted first.
    const child = findItem(folders.items, names.child);
    await openSharing(page, folders, "row");
    if (method === "DELETE") await setRestriction(page, child.id, true);
    const originalModal = await shareModal(page).elementHandle();
    // 2. Make the backend refuse the next restriction change of that kind.
    const route = `**/items/${child.id}/restrict/`;
    await page.route(route, (intercept) =>
      intercept.request().method() === method
        ? intercept.fulfill({
            status: 403,
            contentType: "application/json",
            body: JSON.stringify({ detail: "Restriction permission denied" }),
          })
        : intercept.continue(),
    );
    // 3. Confirm the change and wait for the refused response.
    const confirm = await askRestriction(page, method === "POST");
    const response = page.waitForResponse(
      (result) =>
        result.url().endsWith(`/${child.id}/restrict/`) &&
        result.status() === 403,
    );
    await confirm.click();
    await response;
    // 4. The backend's error is shown, the same share modal stays open and
    //    the folder keeps its previous state.
    await expect(
      page.getByText("Restriction permission denied", { exact: true }),
    ).toBeVisible();
    await expect(shareModal(page)).toBeVisible();
    expect(
      await originalModal!.evaluate((element) => element.isConnected),
    ).toBe(true);
    await expectParentEntry(page, folders, method === "DELETE");
    // 5. Once the backend accepts again, retrying from that modal succeeds.
    await page.unroute(route);
    await setRestriction(page, child.id, method === "POST");
    await expectParentEntry(page, folders, method === "POST");
  });
}

test("files and ordinary root folders have no restriction control", async ({
  page,
  folders,
}) => {
  // Only folders with a parent to inherit from can be restricted. Check a
  // file, then a folder sitting at the root of "My files".
  for (const [parent, title] of [
    [folders.parent.id, names.file],
    ["my-files", names.parent],
  ]) {
    // 1. Open the item's share modal from its row.
    await page.goto(itemUrl(parent));
    await clickOnRowItemActions(page, title, "Share");
    await expect(shareModal(page)).toBeVisible();
    await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
    // 2. The actions menu, when present for other actions, offers neither
    //    restricting nor reopening.
    const moreActions = shareModal(page).getByRole("button", {
      name: "More actions",
      exact: true,
    });
    if (await moreActions.isVisible()) {
      await moreActions.click();
      await expect(page.getByRole("menu")).toBeVisible();
      await expect(
        page.getByRole("menuitem", { name: /Restrict access|Open access/ }),
      ).toHaveCount(0);
      await page.keyboard.press("Escape");
    }
    await expect(
      shareModal(page).getByRole("button", {
        name: /Restrict access|Open access/,
      }),
    ).toHaveCount(0);
    await shareModal(page)
      .getByRole("button", { name: "close", exact: true })
      .click();
  }
});

test("non-owner administrator cannot restrict a folder", async ({
  page,
  folders,
}) => {
  // 1. Sign in as an administrator of the parent, who is not an owner, and
  //    open the folder's share modal.
  await login(page, "administrator@example.com");
  await openSharing(page, folders, "row");
  await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
  // 2. Administrators have a share actions menu, but without restriction.
  await shareModal(page)
    .getByRole("button", { name: "More actions", exact: true })
    .click();
  await expect(page.getByRole("menu")).toBeVisible();
  await expect(
    page.getByRole("menuitem", { name: /Restrict access|Open access/ }),
  ).toHaveCount(0);
  // 3. The backend agrees: the restrict ability is refused.
  const child = findItem(folders.items, names.child);
  const response = await page.request.get(`${API}/items/${child.id}/`);
  expect((await response.json()).abilities.restrict).toBe(false);
});

for (const email of ["inherited@example.com", "direct@example.com"]) {
  test(`${email}: non-owner reader or editor cannot restrict`, async ({
    page,
    folders,
  }) => {
    // 1. Sign in as a reader or an editor of the folder and open its share
    //    modal.
    await login(page, email);
    await openSharing(page, folders, "row");
    await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
    // 2. They get no share actions menu at all, so no way to restrict.
    await expect(
      shareModal(page).getByRole("button", {
        name: "More actions",
        exact: true,
      }),
    ).toHaveCount(0);
    // 3. The backend agrees: the restrict ability is refused.
    const child = findItem(folders.items, names.child);
    expect(
      (await (await page.request.get(`${API}/items/${child.id}/`)).json())
        .abilities.restrict,
    ).toBe(false);
  });
}

test("restriction removes inherited access and preserves the direct editor grant", async ({
  page,
  browser,
  folders,
}) => {
  // 1. Sign in two more users, each in their own browser context: a reader
  //    inheriting access from the parent and an editor granted directly on
  //    the folder.
  const contexts = await Promise.all([
    browser.newContext(),
    browser.newContext(),
  ]);
  try {
    const [reader, editor] = await Promise.all(
      contexts.map((context) => context.newPage()),
    );
    await login(reader, "inherited@example.com");
    await login(editor, "direct@example.com");
    const child = findItem(folders.items, names.child);
    const contents = await listItems(page, `items/${child.id}/children/`);
    // 2. Before the restriction, both can open the folder and see its file.
    for (const user of [reader, editor]) {
      await user.goto(itemUrl(child.id));
      await expect(
        user.getByRole("row", { name: /Child document/ }),
      ).toBeVisible();
    }
    // 3. The owner restricts the folder.
    await openSharing(page, folders, "row");
    await setRestriction(page, child.id, true);
    // 4. The reader lost access: opening the entry from the parent shows the
    //    no-access preview, and the backend refuses the folder's listing,
    //    its file and that file's download.
    await reader.goto(itemUrl(folders.parent.id));
    await reader.getByRole("row", { name: new RegExp(names.child) }).dblclick();
    await expect(reader.locator(".file-preview-no-access")).toBeVisible();
    for (const path of [
      `items/${child.id}/children/`,
      `items/${contents[0].id}/`,
      `items/${contents[0].id}/download/`,
    ]) {
      expect([403, 404]).toContain(
        (await reader.request.get(`${API}/${path}`)).status(),
      );
    }
    // 5. The editor is unaffected: the content is still listed and they can
    //    still create items in the folder.
    await editor.reload();
    await expect(
      editor.getByRole("row", { name: /Child document/ }),
    ).toBeVisible();
    expect(
      (await (await editor.request.get(`${API}/items/${child.id}/`)).json())
        .abilities.children_create,
    ).toBe(true);
    // 6. Once the owner reopens the folder, both users reach it again and
    //    the editor's role is intact in the share modal.
    await setRestriction(page, child.id, false);
    for (const user of [reader, editor]) {
      await user.goto(itemUrl(child.id));
      await expect(
        user.getByRole("row", { name: /Child document/ }),
      ).toBeVisible();
    }
    await expect(
      shareModal(page)
        .getByTestId("share-member-item")
        .filter({ hasText: "Direct Editor" }),
    ).toContainText("Editor");
  } finally {
    await Promise.all(contexts.map((context) => context.close()));
  }
});

test("expanded Favorites refresh after restriction without reloading the page", async ({
  page,
  folders,
}) => {
  // 1. Expand Favorites and the starred parent in the sidebar. The folder
  //    then appears twice in the tree: as a favorite of its own and as a
  //    child of the starred parent.
  await page.goto(itemUrl(folders.parent.id));
  await openTreeNode(page, "Starred", true);
  await openTreeNode(page, names.parent, true);
  const child = findItem(folders.items, names.child);
  // 2. Open sharing from the grid, then restrict and reopen the folder.
  await clickOnRowItemActions(page, names.child, "Share");
  for (const restricted of [true, false]) {
    await setRestriction(page, child.id, restricted);
    await expectParentEntry(page, folders, restricted);
    // 3. The favorite is neither lost nor duplicated, and both tree nodes
    //    are still there.
    const favorites = await listItems(page, "items/favorites/");
    expect(favorites.filter((item) => item.id === child.id)).toHaveLength(1);
    await expect(
      page
        .getByRole("treeitem", { includeHidden: true })
        .filter({ has: page.getByText(names.child, { exact: true }) }),
    ).toHaveCount(2);
    const copies = page
      .getByRole("treeitem", { includeHidden: true })
      .filter({ has: page.getByText(names.child, { exact: true }) });
    // 4. Both nodes switch icon without a reload: the plain folder image
    //    gives way to the restricted folder icon, and back.
    await expect(
      copies.locator(".explorer__tree__item__content > img.c__file-icon"),
    ).toHaveCount(restricted ? 0 : 2);
  }
  // 5. Close sharing: the refreshed node under the parent still navigates
  //    to the folder and its content.
  await shareModal(page)
    .getByRole("button", { name: "close", exact: true })
    .click();
  await page
    .getByRole("treeitem")
    .filter({ has: page.getByText(names.child, { exact: true }) })
    .and(page.locator('[aria-level="3"]'))
    .click();
  await expect(page).toHaveURL(new RegExp(child.id));
  await expect(page.getByRole("row", { name: /Child document/ })).toBeVisible();
});
