import { expect, Page } from "@playwright/test";

export const getRowItem = async (page: Page, itemName: string) => {
  const row = page
    .getByRole("row", { name: itemName })
    .filter({ hasText: itemName })
    .first();

  await expect(row).toBeVisible();
  return row;
};

export const getRowItemActions = async (page: Page, itemName: string) => {
  const row = await getRowItem(page, itemName);
  const actions = row
    .getByRole("button", {
      name: `More actions for ${itemName}`,
      exact: true,
    })
    .nth(1);
  await expect(actions).toBeVisible();
  return actions;
};

export const clickOnRowItemActions = async (
  page: Page,
  itemName: string,
  actionName: string
) => {
  const actions = await getRowItemActions(page, itemName);
  await actions.click({ force: true }); // Because dnd-kit add an aria-disabled attribute on parent and playwright don't interact with it
  const action = page.getByRole("menuitem", { name: "Info" });
  await expect(action).toBeVisible();
  await action.click();
};
