import { expect, Page } from "@playwright/test";

export const getItemTree = async (
  page: Page,
  itemTitle: string,
  isVisible: boolean = true
) => {
  const item = page.getByRole("treeitem").filter({ hasText: itemTitle });
  let itemTree = item.first();
  if (isVisible) {
    await expect(itemTree).toBeVisible();
  } else {
    await expect(itemTree).not.toBeVisible();
  }
  return itemTree;
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

export const openTreeNode = async (page: Page, itemTitle: string) => {
  const item = await getItemTree(page, itemTitle);
  await expect(item).toBeVisible();

  // Check if node is already open (has keyboard_arrow_down icon)
  const downArrow = item.getByText("keyboard_arrow_down");
  const isOpen = await downArrow.isVisible().catch(() => false);

  if (isOpen) {
    // Node is already open, nothing to do
    return;
  }

  // Node is closed, open it
  const arrow = item.getByText("keyboard_arrow_right");
  await expect(arrow).toBeVisible();
  await arrow.click();
};

export const clickOnItemInTree = async (page: Page, itemTitle: string) => {
  const item = await getItemTree(page, itemTitle);
  await expect(item).toBeVisible();
  await item.click();
  await expectTreeItemIsSelected(page, itemTitle);
};

export const expectTreeItemIsSelected = async (
  page: Page,
  itemTitle: string,
  isSelected: boolean = true
) => {
  const item = await getItemTree(page, itemTitle);
  await expect(item).toHaveAttribute(
    "aria-selected",
    isSelected ? "true" : "false"
  );
};

export const deleteFolderInTree = async (page: Page, itemTitle: string) => {
  await clickOnMoreActionsButtonFromItem(page, itemTitle);
  await page.getByRole("menuitem", { name: "Delete" }).click();
  await expect(page.getByText("Item deleted")).toBeVisible();
};

export const deleteWorkspaceInTree = async (page: Page, itemTitle: string) => {
  await clickOnMoreActionsButtonFromItem(page, itemTitle);
  await page.getByRole("menuitem", { name: "Delete" }).click();
};
