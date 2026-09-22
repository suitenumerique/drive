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

for (const path of [
  "grid to grid",
  "grid to Favorites",
  "tree to tree",
] as const) {
  test(`${path}: drops resolve the restriction target, including grid multi-selection`, async ({
    page,
    folders,
  }) => {
    await page.goto(itemUrl(folders.parent.id));
    const target = findItem(folders.items, names.accessible);
    const sources =
      path === "grid to grid"
        ? ["Movable one", "Movable two"]
        : ["Movable one"];
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
    if (sources.length === 2) {
      await (await getRowItem(page, sources[0])).click();
      await (
        await getRowItem(page, sources[1])
      ).click({ modifiers: ["ControlOrMeta"] });
      await expect(page.locator("tr.selected")).toHaveCount(2);
    }
    await pointerDrop(page, source, destination);
    const modal = page.getByRole("dialog", { name: "Move confirmation modal" });
    await expect(modal).toBeVisible();
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
    await (await getRowItem(page, names.accessible)).dblclick();
    await expect(page).toHaveURL(new RegExp(target.target!.id));
    for (const title of sources)
      await expect(await getRowItem(page, title)).toBeVisible();
  });
}

for (const destination of [names.denied, names.deleted, names.readOnly]) {
  test(`${destination}: grid and tree destinations reject moves`, async ({
    page,
    folders,
  }) => {
    await page.goto(itemUrl(folders.parent.id));
    await openTreeNode(page, "Starred", true);
    const moves: string[] = [];
    page.on("request", (request) => {
      if (request.url().endsWith("/move/")) moves.push(request.url());
    });
    const source = (await getRowItem(page, "Movable one"))
      .getByRole("cell")
      .first();
    for (const target of [
      (await getRowItem(page, destination)).getByRole("cell").first(),
      (await getItemTree(page, destination)).getByTestId("tree_item_content"),
    ]) {
      await pointerDrop(page, source, target);
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
  await page.goto(itemUrl(folders.parent.id));
  await openTreeNode(page, "Starred", true);
  const source = (await getRowItem(page, names.accessible))
    .getByRole("cell")
    .first();
  const moves: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/move/")) moves.push(request.url());
  });
  for (const title of [names.accessible, "Cycle descendant"]) {
    await pointerDrop(
      page,
      source,
      (await getItemTree(page, title)).getByTestId("tree_item_content"),
    );
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
