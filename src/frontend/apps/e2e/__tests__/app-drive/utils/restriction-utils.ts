import { expect, Locator, Page, test as base } from "@playwright/test";
import { clearDb, login, runFixture, runTarget } from "../utils-common";
import { clickOnRowItemActions, getRowItem } from "../utils-embedded-grid";
import { clickOnBreadcrumbButtonAction } from "../utils-explorer";
import { clickOnMoreActionsButtonFromItem, openTreeNode } from "../utils-tree";

export const API = "http://localhost:8071/api/v1.0";

/**
 * World seeded by the `e2e_fixture_restrictions` backend command.
 *
 * Restricting a folder detaches it from its parent's inherited accesses: the
 * parent then lists a "restriction" entry whose `target` is the real folder.
 *
 * Restrictions parent      owner: drive@example.com ("Owner"), starred
 * │                        readers: inherited@ ("Inherited Reader"), direct@
 * │                        administrator: administrator@ ("Administrator")
 * ├─ Restrictable folder   plain folder, starred, holds "Child document";
 * │                        direct@ ("Direct Editor") is editor on it directly
 * ├─ Normal folder, Movable one, Movable two, Ordinary document (file)
 * └─ restriction entries, all starred by the owner:
 *    ├─ Accessible restricted    target owned by the owner; holds the starred
 *    │                           "Cycle descendant"
 *    ├─ Confidential.folder.v2   target owned by someone else, no access
 *    ├─ Read-only restricted     owner is only reader on the target
 *    ├─ Deleted restricted       target is in the trash, the entry is stale
 *    └─ Link restricted          target reachable by any signed-in user through
 *                                its link (used with link-only@example.com)
 */
export const names = {
  parent: "Restrictions parent",
  child: "Restrictable folder",
  normal: "Normal folder",
  accessible: "Accessible restricted",
  denied: "Confidential.folder.v2",
  deleted: "Deleted restricted",
  readOnly: "Read-only restricted",
  link: "Link restricted",
  file: "Ordinary document",
} as const;

export type RestrictionItem = {
  id: string;
  title: string;
  type: "folder" | "file" | "restriction";
  is_restricted: boolean;
  abilities: Record<string, boolean>;
  target: null | {
    id: string;
    can_access: boolean;
    deleted: boolean;
    abilities: Record<string, boolean>;
  };
};
export type RestrictionFixture = {
  parent: RestrictionItem;
  items: RestrictionItem[];
};

/** Reads a paginated items endpoint as the user signed in on `page`. */
export async function listItems(page: Page, path: string) {
  const response = await page.request.get(`${API}/${path}`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()).results as RestrictionItem[];
}

/** Picks an item by title, failing loudly when the fixture lacks it. */
export function findItem(items: RestrictionItem[], title: string) {
  const item = items.find((candidate) => candidate.title === title);
  expect(item, `fixture item ${title}`).toBeDefined();
  return item!;
}

/**
 * `folders` fixture: resets the database, seeds the world described above,
 * signs in as the owner and exposes the parent folder and its children.
 */
export const test = base.extend<{ folders: RestrictionFixture }>({
  folders: async ({ page }, provide) => {
    // Check the running backend BEFORE clearing or seeding any records.
    await runTarget("is-e2e-backend-running");
    await clearDb();
    await runFixture("e2e_fixture_restrictions");
    await login(page, "drive@example.com");
    const roots = await listItems(page, "items/?page_size=100");
    const parent = findItem(roots, names.parent);
    const items = await listItems(page, `items/${parent.id}/children/`);
    await provide({ parent, items });
  },
});

export const itemUrl = (id: string) => `/explorer/items/${id}`;
export const shareModal = (page: Page) =>
  page.getByLabel("Share modal", { exact: true });
/** The "Restrict access" / "Open access" confirmation above the share modal. */
export const confirmation = (page: Page) =>
  page
    .getByRole("dialog")
    .filter({ has: page.locator(".c__share-access-confirmation-modal") });

/** Every place in the explorer from which the share modal can be opened. */
export const entryPoints = [
  "row",
  "context",
  "breadcrumb",
  "mobile breadcrumb",
  "favorites",
  "right panel",
] as const;
export type EntryPoint = (typeof entryPoints)[number];

/**
 * Opens the share modal of `title` (the restrictable folder by default) as a
 * user would from the given entry point.
 */
export async function openSharing(
  page: Page,
  folders: RestrictionFixture,
  entry: EntryPoint,
  title: string = names.child,
) {
  const item = findItem(folders.items, title);
  if (entry === "mobile breadcrumb")
    await page.setViewportSize({ width: 375, height: 667 });
  // Breadcrumb entry points act on the current folder, so start inside the
  // folder itself; every other entry point starts from its parent listing.
  await page.goto(
    itemUrl(
      entry.includes("breadcrumb")
        ? (item.target?.id ?? item.id)
        : folders.parent.id,
    ),
  );
  if (entry === "row") {
    // Select the row first: the restriction must later clear that selection.
    await (await getRowItem(page, title)).click();
    await expect(page.locator("tr.selected")).toHaveCount(1);
    await clickOnRowItemActions(page, title, "Share");
  } else if (entry === "context") {
    await (await getRowItem(page, title)).click({ button: "right" });
    await page.getByRole("menuitem", { name: "Share", exact: true }).click();
  } else if (entry === "breadcrumb") {
    // Selecting a child proves the breadcrumb shares the folder, not the row.
    await page.getByRole("row", { name: /Child document/ }).click();
    await expect(page.locator("tr.selected")).toHaveCount(1);
    await clickOnBreadcrumbButtonAction(page, "Share");
  } else if (entry === "mobile breadcrumb") {
    await page
      .locator(".explorer__content__breadcrumbs--mobile")
      .getByRole("button", { name: "more_vert" })
      .click();
    await page.getByRole("menuitem", { name: "Share", exact: true }).click();
  } else if (entry === "favorites") {
    await openTreeNode(page, "Starred", true);
    await clickOnMoreActionsButtonFromItem(page, title);
    await page.getByRole("menuitem", { name: "Share", exact: true }).click();
  } else {
    // Right panel: open the item information, then its share button.
    await clickOnRowItemActions(page, title, "Info");
    await page
      .getByTestId("right-panel")
      .getByRole("button", { name: /group|Share/ })
      .click();
  }
  await expect(shareModal(page)).toBeVisible();
}

/**
 * Picks "Restrict access" or "Open access" in the share modal menu and returns
 * the confirmation button, without clicking it.
 */
export async function askRestriction(page: Page, restricted: boolean) {
  const label = restricted ? "Restrict access" : "Open access";
  await shareModal(page)
    .getByRole("button", { name: "More actions", exact: true })
    .click();
  await page.getByRole("menuitem", { name: label }).click();
  await expect(confirmation(page)).toBeVisible();
  return confirmation(page).getByRole("button", { name: label, exact: true });
}

/**
 * Restricts or reopens a folder from the already opened share modal and waits
 * until the modal reflects the new state.
 */
export async function setRestriction(
  page: Page,
  folderId: string,
  restricted: boolean,
) {
  const confirm = await askRestriction(page, restricted);
  // Restricting POSTs to the folder's restrict endpoint, reopening DELETEs it.
  const response = page.waitForResponse(
    (result) =>
      result.url().endsWith(`/items/${folderId}/restrict/`) &&
      result.request().method() === (restricted ? "POST" : "DELETE"),
  );
  await confirm.click();
  expect((await response).ok()).toBeTruthy();
  // Only the confirmation closes; sharing stays open and shows the new state.
  await expect(confirmation(page)).not.toBeVisible();
  await expect(shareModal(page)).toBeVisible();
  await expect(
    shareModal(page).getByText("This item has restricted access", {
      exact: true,
    }),
  ).toHaveCount(restricted ? 1 : 0);
  // The members list is hidden during cache refresh; wait for it to return.
  await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
}

/**
 * Checks, through the API, how the parent lists the restrictable folder: as a
 * restriction entry targeting it once restricted, as the folder itself
 * otherwise. Returns that entry.
 */
export async function expectParentEntry(
  page: Page,
  folders: RestrictionFixture,
  restricted: boolean,
) {
  const child = findItem(folders.items, names.child);
  const items = await listItems(page, `items/${folders.parent.id}/children/`);
  const entry = findItem(items, names.child);
  expect(entry.type).toBe(restricted ? "restriction" : "folder");
  expect(restricted ? entry.target?.id : entry.id).toBe(child.id);
  return entry;
}

// Tree rows shift while sibling nodes finish loading; dragging from a stale
// position misses the row, so wait until it stops moving.
async function settledBox(locator: Locator) {
  let previous = "";
  await expect
    .poll(
      async () => {
        const current = JSON.stringify(await locator.boundingBox());
        const settled = current !== "null" && current === previous;
        previous = current;
        return settled;
      },
      { intervals: [250] },
    )
    .toBe(true);
  return (await locator.boundingBox())!;
}

/**
 * Drags `source` onto `destination` with real pointer events, as the explorer
 * uses two drag systems: an overlay for grid rows, native dragging in the tree.
 */
export async function pointerDrop(
  page: Page,
  source: Locator,
  destination: Locator,
) {
  await source.scrollIntoViewIfNeeded();
  await destination.scrollIntoViewIfNeeded();
  const from = await settledBox(source);
  const to = await settledBox(destination);
  // 1. Press on the source and move far enough to start a drag.
  const x = from.x + Math.min(from.width / 2, 110);
  const y = from.y + from.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 30, y + 8, { steps: 5 });
  const treeSource = await source.evaluate(
    (element) => !!element.closest("[role=treeitem]"),
  );
  // 2. Wait for the drag to be visibly in progress before travelling.
  await expect(
    page.locator(
      treeSource
        ? '.c__tree-view--node.isDragging[draggable="true"]'
        : ".explorer__drag-overlay",
    ),
  ).toBeVisible();
  // 3. Travel to the destination in small steps so hover handlers fire.
  await page.mouse.move(
    to.x + Math.min(to.width / 2, 110),
    to.y + to.height / 2,
    { steps: 25 },
  );
  const dropX = to.x + Math.min(to.width / 2, 110);
  const dropY = to.y + to.height / 2;
  // Native tree dragging needs a dragover after entering the destination.
  await page.mouse.move(dropX + 1, dropY);
  if (treeSource) {
    // WebKit sometimes drops that dragover, so keep nudging until the row
    // acknowledges the drop.
    let nudge = 0;
    await expect
      .poll(async () => {
        nudge = (nudge + 1) % 4;
        await page.mouse.move(dropX + nudge, dropY);
        return destination.evaluate((element) =>
          element
            .closest(".c__tree-view--node")
            ?.classList.contains("willReceiveDrop"),
        );
      })
      .toBe(true);
  }
  // 4. Release to drop.
  await page.mouse.up();
}
