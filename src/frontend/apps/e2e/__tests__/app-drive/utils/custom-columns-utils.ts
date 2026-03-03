import { expect, Locator, Page } from "@playwright/test";

/**
 * Get the <th> element for a customizable column slot.
 */
export const getColumnHeader = (page: Page, slot: 1 | 2): Locator => {
  return page.locator(`th.explorer__grid__th--info-col-${slot}`);
};

/**
 * Change the type of a customizable column via its dropdown menu.
 */
export const changeColumnType = async (
  page: Page,
  slot: 1 | 2,
  columnLabel: string,
) => {
  const header = getColumnHeader(page, slot);
  // Click the dropdown button inside the header (first button = dropdown trigger)
  const dropdownButton = header
    .locator(".explorer__grid__header button")
    .first();
  await dropdownButton.click();

  // Select the desired column type — use exact to avoid "Created" matching "Created by"
  const menuItem = page.getByRole("menuitem", {
    name: columnLabel,
    exact: true,
  });
  await expect(menuItem).toBeVisible();
  await menuItem.click();
};

/**
 * Assert that a column header displays the expected label.
 */
export const expectColumnHeaderLabel = async (
  page: Page,
  slot: 1 | 2,
  expectedLabel: string,
) => {
  const header = getColumnHeader(page, slot);
  const button = header.locator(".explorer__grid__header button").first();
  await expect(button).toContainText(expectedLabel);
};

/**
 * Click a sort button via native JS click (bypasses tooltip overlay).
 * Waits for the aria-label to change, confirming the click was processed.
 */
const clickSortAndWaitForStateChange = async (
  sortButton: Locator,
  nextLabel: string,
) => {
  // Use evaluate to trigger a native click — tooltips can intercept Playwright clicks
  await sortButton.evaluate((el) => (el as HTMLButtonElement).click());
  // Wait for the button aria-label to change (state updated)
  await expect(sortButton).toHaveAttribute("aria-label", nextLabel, {
    timeout: 10000,
  });
};

const SORT_TRANSITIONS: Record<string, string> = {
  "Sort ascending": "Sort descending",
  "Sort descending": "Reset sorting",
  "Reset sorting": "Sort ascending",
};

/**
 * Click the sort button for the "Name" column header.
 */
export const clickNameSortButton = async (page: Page) => {
  const nameHeader = page.locator("th").nth(1); // second th = Name column
  const sortButton = nameHeader.locator(
    ".explorer__grid__header button[aria-label]",
  );
  const ariaLabel = await sortButton.getAttribute("aria-label");
  const nextLabel = SORT_TRANSITIONS[ariaLabel ?? ""];
  if (nextLabel) {
    await clickSortAndWaitForStateChange(sortButton, nextLabel);
  } else {
    await sortButton.evaluate((el) => (el as HTMLButtonElement).click());
  }
};

/**
 * Click the sort button for a customizable column (slot 1 or 2).
 */
export const clickColumnSortButton = async (page: Page, slot: 1 | 2) => {
  const header = getColumnHeader(page, slot);
  // Second button in the header = sort button (first = dropdown trigger)
  const sortButton = header.locator(".explorer__grid__header button").nth(1);
  const ariaLabel = await sortButton.getAttribute("aria-label");
  const nextLabel = SORT_TRANSITIONS[ariaLabel ?? ""];
  if (nextLabel) {
    await clickSortAndWaitForStateChange(sortButton, nextLabel);
  } else {
    await sortButton.evaluate((el) => (el as HTMLButtonElement).click());
  }
};

/**
 * Get all visible row names in order from the grid.
 */
export const getRowNamesInOrder = async (page: Page): Promise<string[]> => {
  const nameElements = page.locator(
    "tbody tr.selectable .explorer__grid__item__name",
  );
  const count = await nameElements.count();
  if (count === 0) return [];
  const names: string[] = [];
  for (let i = 0; i < count; i++) {
    const text = (await nameElements.nth(i).textContent()) ?? "";
    names.push(text.trim());
  }
  return names;
};

/**
 * Wait for row names to match the expected order (retries automatically).
 */
export const expectRowNamesInOrder = async (
  page: Page,
  expectedNames: string[],
) => {
  await expect
    .poll(async () => getRowNamesInOrder(page), { timeout: 10000 })
    .toEqual(expectedNames);
};

/**
 * Get the text content of a cell in a specific row at a given column slot.
 * Slot 1 = first info column (3rd td), slot 2 = second info column (4th td).
 */
export const getCellText = async (
  page: Page,
  rowName: string,
  slot: 1 | 2,
): Promise<string> => {
  const row = page
    .getByRole("row", { name: rowName })
    .filter({ hasText: rowName })
    .first();
  await expect(row).toBeVisible();
  // td indices: 0=mobile, 1=title, 2=info-col-1, 3=info-col-2, 4=actions
  const cellIndex = slot === 1 ? 2 : 3;
  const cell = row.locator("td").nth(cellIndex);
  return ((await cell.textContent()) ?? "").trim();
};
