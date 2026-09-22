import { expect } from "@playwright/test";
import { getRowItem } from "./utils-embedded-grid";
import { getItemTree, openTreeNode } from "./utils-tree";
import {
  findItem,
  itemUrl,
  listItems,
  names,
  pointerDrop,
  test,
} from "./utils/restriction-utils";

// Dropping onto a restriction entry must move items into the real folder the
// entry points to, whichever drag source and drop surface are used.
for (const path of [
  "grid to grid",
  "grid to Favorites",
  "tree to tree",
] as const) {
  test(`${path}: drops resolve the restriction target, including grid multi-selection`, async ({
    page,
    folders,
  }) => {
    // 1. Open the parent folder. The destination is the restriction entry
    //    whose target the owner can write to. Only the grid supports dragging
    //    several items, so that path moves two folders at once.
    await page.goto(itemUrl(folders.parent.id));
    const target = findItem(folders.items, names.accessible);
    const sources =
      path === "grid to grid"
        ? ["Movable one", "Movable two"]
        : ["Movable one"];
    // 2. Expand the sidebar nodes holding the tree source and destination:
    //    the entry is starred, the tree source sits under the starred parent.
    if (path !== "grid to grid") await openTreeNode(page, "Starred", true);
    if (path === "tree to tree") await openTreeNode(page, names.parent, true);
    const source =
      path === "tree to tree"
        ? (await getItemTree(page, sources[0])).getByTestId("tree_item_content")
        : (await getRowItem(page, sources[0])).getByRole("cell").first();
    const destination =
      path === "grid to grid"
        ? (await getRowItem(page, names.accessible)).getByRole("cell").first()
        : (await getItemTree(page, names.accessible)).getByTestId(
            "tree_item_content",
          );
    // 3. For the multi-selection path, select both rows before dragging.
    if (sources.length === 2) {
      await (await getRowItem(page, sources[0])).click();
      await (
        await getRowItem(page, sources[1])
      ).click({ modifiers: ["ControlOrMeta"] });
      await expect(page.locator("tr.selected")).toHaveCount(2);
    }
    // 4. Drop onto the restriction entry: moving into a folder with different
    //    accesses asks for confirmation.
    await pointerDrop(page, source, destination);
    const modal = page.getByRole("dialog", { name: "Move confirmation modal" });
    await expect(modal).toBeVisible();
    // 5. Confirm, listening to one move request per dragged item to check
    //    where each one is sent.
    const moves = sources.map((title) => {
      const sourceId = findItem(folders.items, title).id;
      return page.waitForResponse(
        (response) =>
          response.url().endsWith(`${sourceId}/move/`) &&
          response.request().method() === "POST",
      );
    });
    await modal.getByRole("button", { name: "Move anyway" }).click();
    const responses = await Promise.all(moves);
    // 6. Each item is moved into the entry's target folder, never into the
    //    restriction entry itself.
    for (let index = 0; index < responses.length; index++) {
      const response = responses[index];
      expect(new URL(response.url()).pathname).toBe(
        `/api/v1.0/items/${findItem(folders.items, sources[index]).id}/move/`,
      );
      expect(response.ok()).toBe(true);
      expect(response.request().postDataJSON()).toEqual({
        target_item_id: target.target!.id,
      });
    }
    // 7. The moved items leave the parent listing and the backend now lists
    //    them inside the target folder.
    for (const title of sources)
      await expect(
        page.getByRole("row", { name: new RegExp(title) }),
      ).toHaveCount(0);
    const children = await listItems(
      page,
      `items/${target.target!.id}/children/`,
    );
    for (const title of sources)
      expect(findItem(children, title).id).toBe(
        findItem(folders.items, title).id,
      );
    // 8. Opening the entry navigates to the target, where they are displayed.
    await (await getRowItem(page, names.accessible)).dblclick();
    await expect(page).toHaveURL(new RegExp(target.target!.id));
    for (const title of sources)
      await expect(await getRowItem(page, title)).toBeVisible();
  });
}

// Entries whose target is inaccessible, deleted or read-only are not valid
// drop destinations, in the grid as well as in the Favorites tree.
for (const destination of [names.denied, names.deleted, names.readOnly]) {
  test(`${destination}: grid and tree destinations reject moves`, async ({
    page,
    folders,
  }) => {
    // 1. Open the parent folder and expand Favorites, where the same entry
    //    also appears as a tree node.
    await page.goto(itemUrl(folders.parent.id));
    await openTreeNode(page, "Starred", true);
    // 2. Record every move request: a rejected drop must not send any.
    const moves: string[] = [];
    page.on("request", (request) => {
      if (request.url().endsWith("/move/")) moves.push(request.url());
    });
    // 3. Drag a movable folder onto the entry, first in the grid, then in
    //    the tree.
    const source = (await getRowItem(page, "Movable one"))
      .getByRole("cell")
      .first();
    for (const target of [
      (await getRowItem(page, destination)).getByRole("cell").first(),
      (await getItemTree(page, destination)).getByTestId("tree_item_content"),
    ]) {
      await pointerDrop(page, source, target);
      // 4. The drop is ignored: no confirmation, the drag ends cleanly and
      //    the folder is still listed in the parent.
      await expect(
        page.getByRole("dialog", { name: "Move confirmation modal" }),
      ).toHaveCount(0);
      await expect(page.locator(".explorer__drag-overlay")).toHaveCount(0);
      const children = await listItems(
        page,
        `items/${folders.parent.id}/children/`,
      );
      expect(findItem(children, "Movable one").id).toBe(
        findItem(folders.items, "Movable one").id,
      );
      expect(moves).toEqual([]);
    }
  });
}

test("a restriction entry cannot be dropped into its own target or descendant", async ({
  page,
  folders,
}) => {
  // 1. Open the parent folder and expand Favorites, which lists both the
  //    entry and a folder located inside its target.
  await page.goto(itemUrl(folders.parent.id));
  await openTreeNode(page, "Starred", true);
  const source = (await getRowItem(page, names.accessible))
    .getByRole("cell")
    .first();
  // 2. Record every move request: a rejected drop must not send any.
  const moves: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/move/")) moves.push(request.url());
  });
  // 3. Drag the entry onto itself, then onto its target's descendant. Both
  //    would put the folder inside its own tree.
  for (const title of [names.accessible, "Cycle descendant"]) {
    await pointerDrop(
      page,
      source,
      (await getItemTree(page, title)).getByTestId("tree_item_content"),
    );
    // 4. Nothing happens: no confirmation, no request, and the entry stays
    //    in the parent.
    await expect(
      page.getByRole("dialog", { name: "Move confirmation modal" }),
    ).toHaveCount(0);
    const children = await listItems(
      page,
      `items/${folders.parent.id}/children/`,
    );
    expect(findItem(children, names.accessible).id).toBe(
      findItem(folders.items, names.accessible).id,
    );
    expect(moves).toEqual([]);
  }
});
