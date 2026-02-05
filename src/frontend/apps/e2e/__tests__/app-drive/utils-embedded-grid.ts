import { expect } from "@playwright/test";
import { PageOrLocator } from "./utils/types-utils";

const getRowLocator = (page: PageOrLocator, itemName: string) => {
  return page
    .getByRole("row", { name: itemName })
    .filter({ hasText: itemName })
    .first();
};

export const expectRowItem = async (page: PageOrLocator, itemName: string) => {
  const row = getRowLocator(page, itemName);
  await expect(row).toBeVisible();
};

export const expectRowItemIsNotVisible = async (
  page: PageOrLocator,
  itemName: string
) => {
  const row = getRowLocator(page, itemName);
  await expect(row).not.toBeVisible();
};

export const getRowItem = async (page: PageOrLocator, itemName: string) => {
  const row = getRowLocator(page, itemName);
  await expect(row).toBeVisible();
  return row;
};

export const getRowItemActions = async (
  page: PageOrLocator,
  itemName: string
) => {
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
  page: PageOrLocator,
  itemName: string,
  actionName: string
) => {
  const actions = await getRowItemActions(page, itemName);
  await actions.click({ force: true }); // Because dnd-kit add an aria-disabled attribute on parent and playwright don't interact with it
  const action = page.getByRole("menuitem", { name: actionName });
  await expect(action).toBeVisible();
  await action.click();
};
