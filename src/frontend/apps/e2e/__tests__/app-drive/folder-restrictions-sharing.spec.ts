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

for (const entryPoint of entryPoints) {
  test(`${entryPoint}: restrict and reopen without remounting sharing`, async ({
    page,
    folders,
  }) => {
    const child = findItem(folders.items, names.child);
    await openSharing(page, folders, entryPoint);
    const originalModal = await shareModal(page).elementHandle();
    const members = shareModal(page).getByTestId("members-list");
    await expect(members).toContainText("Inherited Reader");
    await setRestriction(page, child.id, true);
    expect(
      await originalModal!.evaluate((element) => element.isConnected),
    ).toBe(true);
    const restrictedEntry = await expectParentEntry(page, folders, true);
    await expect(page.locator("tr.selected")).toHaveCount(0);
    if (!entryPoint.includes("breadcrumb")) {
      await expect(page.locator(`tr[data-id="${child.id}"]`)).toHaveCount(0);
      await expect(
        page.locator(`tr[data-id="${restrictedEntry.id}"]`),
      ).toBeVisible();
    }
    await expect(members).not.toContainText("Inherited Reader");
    await expect(
      members
        .getByTestId("share-member-item")
        .filter({ hasText: "Direct Editor" }),
    ).toContainText("Editor");
    if (entryPoint === "right panel")
      await expect(page.getByTestId("right-panel")).not.toBeVisible();
    if (entryPoint.includes("breadcrumb")) {
      await expect(page).toHaveURL(new RegExp(child.id));
      const breadcrumbs =
        entryPoint === "breadcrumb"
          ? page.getByTestId("explorer-breadcrumbs")
          : page.locator(".explorer__content__breadcrumbs--mobile");
      await expect(breadcrumbs).not.toContainText(names.parent);
    }
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
  const entry = findItem(folders.items, names.accessible);
  await openSharing(page, folders, "row", names.accessible);
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/restrict/")) requests.push(request.url());
  });
  await setRestriction(page, entry.target!.id, false);
  await setRestriction(page, entry.target!.id, true);
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
    const title = restrict ? names.child : names.accessible;
    const item = findItem(folders.items, title);
    await openSharing(page, folders, "row", title);
    const requests: string[] = [];
    page.on("request", (request) => {
      if (request.url().endsWith("/restrict/")) requests.push(request.method());
    });
    for (const action of ["Cancel", "close", "Escape"]) {
      await askRestriction(page, restrict);
      if (action === "Escape") await page.keyboard.press("Escape");
      else
        await confirmation(page)
          .getByRole("button", { name: action, exact: true })
          .click();
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
    const child = findItem(folders.items, names.child);
    await openSharing(page, folders, "row");
    if (method === "DELETE") await setRestriction(page, child.id, true);
    const originalModal = await shareModal(page).elementHandle();
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
    const confirm = await askRestriction(page, method === "POST");
    const response = page.waitForResponse(
      (result) =>
        result.url().endsWith(`/${child.id}/restrict/`) &&
        result.status() === 403,
    );
    await confirm.click();
    await response;
    await expect(
      page.getByText("Restriction permission denied", { exact: true }),
    ).toBeVisible();
    await expect(shareModal(page)).toBeVisible();
    expect(
      await originalModal!.evaluate((element) => element.isConnected),
    ).toBe(true);
    await expectParentEntry(page, folders, method === "DELETE");
    await page.unroute(route);
    await setRestriction(page, child.id, method === "POST");
    await expectParentEntry(page, folders, method === "POST");
  });
}

test("files and ordinary root folders have no restriction control", async ({
  page,
  folders,
}) => {
  for (const [parent, title] of [
    [folders.parent.id, names.file],
    ["my-files", names.parent],
  ]) {
    await page.goto(itemUrl(parent));
    await clickOnRowItemActions(page, title, "Share");
    await expect(shareModal(page)).toBeVisible();
    await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
    const importButton = shareModal(page).getByRole("button", {
      name: /Import/,
    });
    if (await importButton.isVisible()) {
      await importButton.click();
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
  await login(page, "administrator@example.com");
  await openSharing(page, folders, "row");
  await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
  await shareModal(page)
    .getByRole("button", { name: /Import/ })
    .click();
  await expect(page.getByRole("menu")).toBeVisible();
  await expect(
    page.getByRole("menuitem", { name: /Restrict access|Open access/ }),
  ).toHaveCount(0);
  const child = findItem(folders.items, names.child);
  const response = await page.request.get(`${API}/items/${child.id}/`);
  expect((await response.json()).abilities.restrict).toBe(false);
});

for (const email of ["inherited@example.com", "direct@example.com"]) {
  test(`${email}: non-owner reader or editor cannot restrict`, async ({
    page,
    folders,
  }) => {
    await login(page, email);
    await openSharing(page, folders, "row");
    await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
    await expect(
      shareModal(page).getByRole("button", {
        name: /Restrict access|Open access|Import contacts/,
      }),
    ).toHaveCount(0);
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
    for (const user of [reader, editor]) {
      await user.goto(itemUrl(child.id));
      await expect(
        user.getByRole("row", { name: /Child document/ }),
      ).toBeVisible();
    }
    await openSharing(page, folders, "row");
    await setRestriction(page, child.id, true);
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
    await editor.reload();
    await expect(
      editor.getByRole("row", { name: /Child document/ }),
    ).toBeVisible();
    expect(
      (await (await editor.request.get(`${API}/items/${child.id}/`)).json())
        .abilities.children_create,
    ).toBe(true);
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
  await page.goto(itemUrl(folders.parent.id));
  await openTreeNode(page, "Starred", true);
  await openTreeNode(page, names.parent, true);
  const child = findItem(folders.items, names.child);
  await clickOnRowItemActions(page, names.child, "Share");
  for (const restricted of [true, false]) {
    await setRestriction(page, child.id, restricted);
    await expectParentEntry(page, folders, restricted);
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
    // Both the direct favorite and the already expanded parent's child refresh.
    await expect(
      copies.locator(".explorer__tree__item__content > img.c__file-icon"),
    ).toHaveCount(restricted ? 0 : 2);
  }
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
