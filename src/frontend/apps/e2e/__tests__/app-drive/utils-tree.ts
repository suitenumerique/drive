import { expect, Page } from "@playwright/test";

export const getItemTree = async (page: Page, itemTitle: string) => {
  const item = page.getByRole("treeitem").filter({ hasText: itemTitle });
  let itemTree = item.first();
  if (itemTitle === "My workspace") {
    itemTree = item.nth(1);
  }
  await expect(itemTree).toBeVisible();
  return itemTree;
};

export const toggleItemInTree = async (page: Page, itemTitle: string) => {
  const item = await getItemTree(page, itemTitle);
  const arrow = item.getByText("keyboard_arrow_right");
  await expect(arrow).toBeVisible();
  await arrow.click();
};

export const getItemContent = async (page: Page, itemTitle: string) => {
  const item = await getItemTree(page, itemTitle);
  const itemContent = item.getByTestId("tree_item_content");
  await expect(itemContent).toBeVisible();
  return itemContent;
};

export const clickOnAddChildrenButtonFromItem = async (
  page: Page,
  itemTitle: string
) => {
  const itemContent = await getItemContent(page, itemTitle);
  await expect(itemContent).toBeVisible();
  await itemContent.hover();
  const addChildrenButton = itemContent.getByRole("button", {
    name: "add_children",
  });
  await expect(addChildrenButton).toBeVisible();
  await addChildrenButton.click();
};

export const clickOnMoreActionsButtonFromItem = async (
  page: Page,
  itemTitle: string
) => {
  const itemContent = await getItemContent(page, itemTitle);
  await expect(itemContent).toBeVisible();
  await itemContent.hover();
  const moreActionsButton = itemContent.getByRole("button", {
    name: "more_actions",
  });
  await expect(moreActionsButton).toBeVisible();
  await moreActionsButton.click();
};

export const addChildrenFromTreeItem = async (
  page: Page,
  itemTitle: string,
  childrenTitle: string
) => {
  await clickOnAddChildrenButtonFromItem(page, itemTitle);
  const modal = page.getByRole("dialog");
  await expect(modal).toBeVisible();
  await page.getByText("Folder name").click();
  await page.getByRole("textbox", { name: "Folder name" }).fill(childrenTitle);
  await page.getByRole("button", { name: "Create" }).click();
};

export const clickOnItemInTree = async (page: Page, itemTitle: string) => {
  const item = await getItemTree(page, itemTitle);
  await expect(item).toBeVisible();
  await item.click();
  await expectTreeItemIsSelected(page, itemTitle);
};

export const expectTreeItemIsSelected = async (
  page: Page,
  itemTitle: string
) => {
  const item = await getItemTree(page, itemTitle);
  await expect(item).toHaveAttribute("aria-selected", "true");
};

export const deleteFolderInTree = async (page: Page, itemTitle: string) => {
  await clickOnMoreActionsButtonFromItem(page, itemTitle);
  await page.getByRole("menuitem", { name: "Delete folder" }).click();
  await expect(page.getByText("Item deleted")).toBeVisible();
};

export const deleteWorkspaceInTree = async (page: Page, itemTitle: string) => {
  await clickOnMoreActionsButtonFromItem(page, itemTitle);
  await page.getByRole("menuitem", { name: "Delete workspace" }).click();
};
