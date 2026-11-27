import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import { expectRowItem } from "./utils-embedded-grid";

test("Switch the explorer to the grid view and keep it after a reload", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "testFolder");

  await page.getByRole("button", { name: "Grid view" }).click();
  await expect(page.getByRole("button", { name: "Grid view" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  const card = page
    .locator(".explorer__grid__card")
    .filter({ hasText: "testFolder" });
  await expect(card).toBeVisible();
  await expect(page.getByRole("row", { name: "testFolder" })).toHaveCount(0);

  await page.reload();
  await expect(card).toBeVisible();

  await card.dblclick();
  await expectExplorerBreadcrumbs(page, ["My files", "testFolder"]);

  await page.getByRole("button", { name: "List view" }).click();
  await clickToMyFiles(page);
  await expectRowItem(page, "testFolder");
});

test("Navigate the grid view with the keyboard", async ({ page }) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  for (const index of [1, 2, 3, 4, 5, 6]) {
    await createFolderInCurrentFolder(page, `folder${index}`);
  }

  await page.getByRole("button", { name: "Grid view" }).click();
  const list = page.getByRole("list", { name: "Grid view" });
  await expect(list.getByRole("listitem")).toHaveCount(6);
  const card = (index: number) =>
    list.locator(".explorer__grid__card").nth(index);
  const columns = await list.evaluate(
    (element) =>
      getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean)
        .length,
  );

  await card(0).click();
  await expect(card(0)).toHaveClass(/selected/);

  // Left and right move to the previous and next item, the focus follows.
  await page.keyboard.press("ArrowRight");
  await expect(card(1)).toHaveClass(/selected/);
  await expect(card(0)).not.toHaveClass(/selected/);
  await expect(card(1)).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await expect(card(0)).toHaveClass(/selected/);
  await expect(card(0)).toBeFocused();

  // Down moves a row down, or to the last item from above an incomplete row.
  await page.keyboard.press("ArrowDown");
  const below = Math.min(columns, 5);
  await expect(card(below)).toHaveClass(/selected/);
  await expect(card(below)).toBeFocused();

  // Shift extends the selection.
  await page.keyboard.press("Shift+ArrowLeft");
  await expect(card(below)).toHaveClass(/selected/);
  await expect(card(below - 1)).toHaveClass(/selected/);
});
