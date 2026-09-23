import { expect, Locator, Page, test as base } from "@playwright/test";
import { clearDb, login, runFixture, runTarget } from "../utils-common";
import { clickOnRowItemActions, getRowItem } from "../utils-embedded-grid";
import { clickOnBreadcrumbButtonAction } from "../utils-explorer";
import { clickOnMoreActionsButtonFromItem, openTreeNode } from "../utils-tree";

export const API = "http://localhost:8071/api/v1.0";
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

export async function listItems(page: Page, path: string) {
  const response = await page.request.get(`${API}/${path}`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()).results as RestrictionItem[];
}

export function findItem(items: RestrictionItem[], title: string) {
  const item = items.find((candidate) => candidate.title === title);
  expect(item, `fixture item ${title}`).toBeDefined();
  return item!;
}

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
export const confirmation = (page: Page) =>
  page
    .getByRole("dialog")
    .filter({ has: page.locator(".c__share-access-confirmation-modal") });

export const entryPoints = [
  "row",
  "context",
  "breadcrumb",
  "mobile breadcrumb",
  "favorites",
  "right panel",
] as const;
export type EntryPoint = (typeof entryPoints)[number];

export async function openSharing(
  page: Page,
  folders: RestrictionFixture,
  entry: EntryPoint,
  title: string = names.child,
) {
  const item = findItem(folders.items, title);
  if (entry === "mobile breadcrumb")
    await page.setViewportSize({ width: 375, height: 667 });
  await page.goto(
    itemUrl(
      entry.includes("breadcrumb")
        ? (item.target?.id ?? item.id)
        : folders.parent.id,
    ),
  );
  if (entry === "row") {
    await (await getRowItem(page, title)).click();
    await expect(page.locator("tr.selected")).toHaveCount(1);
    await clickOnRowItemActions(page, title, "Share");
  } else if (entry === "context") {
    await (await getRowItem(page, title)).click({ button: "right" });
    await page.getByRole("menuitem", { name: "Share", exact: true }).click();
  } else if (entry === "breadcrumb") {
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
    await clickOnRowItemActions(page, title, "Info");
    await page
      .getByTestId("right-panel")
      .getByRole("button", { name: /group|Share/ })
      .click();
  }
  await expect(shareModal(page)).toBeVisible();
}

export async function askRestriction(page: Page, restricted: boolean) {
  const label = restricted ? "Restrict access" : "Open access";
  await shareModal(page)
    .getByRole("button", { name: /Import|Restrict access|Open access/ })
    .click();
  await page.getByRole("menuitem", { name: label }).click();
  await expect(confirmation(page)).toBeVisible();
  return confirmation(page).getByRole("button", { name: label, exact: true });
}

export async function setRestriction(
  page: Page,
  folderId: string,
  restricted: boolean,
) {
  const confirm = await askRestriction(page, restricted);
  const response = page.waitForResponse(
    (result) =>
      result.url().endsWith(`/items/${folderId}/restrict/`) &&
      result.request().method() === (restricted ? "POST" : "DELETE"),
  );
  await confirm.click();
  expect((await response).ok()).toBeTruthy();
  await expect(confirmation(page)).not.toBeVisible();
  await expect(shareModal(page)).toBeVisible();
  await expect(
    shareModal(page).getByText("This folder has restricted access", {
      exact: true,
    }),
  ).toHaveCount(restricted ? 1 : 0);
  // The members list is hidden during cache refresh; wait for it to return.
  await expect(shareModal(page).getByTestId("members-list")).toBeVisible();
}

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

export async function pointerDrop(
  page: Page,
  source: Locator,
  destination: Locator,
) {
  await source.scrollIntoViewIfNeeded();
  await destination.scrollIntoViewIfNeeded();
  const from = await source.boundingBox();
  const to = await destination.boundingBox();
  expect(from).not.toBeNull();
  expect(to).not.toBeNull();
  const x = from!.x + Math.min(from!.width / 2, 110);
  const y = from!.y + from!.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 30, y + 8, { steps: 5 });
  const treeSource = await source.evaluate(
    (element) => !!element.closest("[role=treeitem]"),
  );
  await expect(
    page.locator(
      treeSource
        ? '.c__tree-view--node.isDragging[draggable="true"]'
        : ".explorer__drag-overlay",
    ),
  ).toBeVisible();
  await page.mouse.move(
    to!.x + Math.min(to!.width / 2, 110),
    to!.y + to!.height / 2,
    { steps: 25 },
  );
  // Native tree dragging needs a dragover after entering the destination.
  await page.mouse.move(
    to!.x + Math.min(to!.width / 2, 110) + 1,
    to!.y + to!.height / 2,
  );
  if (treeSource) {
    await expect
      .poll(() =>
        destination.evaluate((element) =>
          element
            .closest(".c__tree-view--node")
            ?.classList.contains("willReceiveDrop"),
        ),
      )
      .toBe(true);
  }
  await page.mouse.up();
}
