import { expect, Page } from "@playwright/test";
import { getItemTree, openTreeNode } from "./utils-tree";
import { getRowItem } from "./utils-embedded-grid";

export const createWorkspace = async (page: Page, workspaceName: string) => {
  await page.getByRole("button", { name: "add Create" }).click();
  await page.getByRole("menuitem", { name: "New workspace" }).click();
  await page.getByRole("textbox", { name: "Workspace name" }).click();
  await page
    .getByRole("textbox", { name: "Workspace name" })
    .fill(workspaceName);
  await page.getByRole("button", { name: "Create" }).click();
  await openTreeNode(page, "Shared Space");
  const newWorkspaceItem = await getItemTree(page, workspaceName);
  await expect(newWorkspaceItem).toBeVisible();
};

export const createFolder = async (page: Page, folderName: string) => {
  await page.getByRole("button", { name: "Create Folder" }).click();
  await page.getByRole("textbox", { name: "Folder name" }).click();
  await page.getByRole("textbox", { name: "Folder name" }).fill(folderName);
  await page.getByRole("button", { name: "Create" }).click();
};

export const createFolderInCurrentFolder = async (
  page: Page,
  folderName: string
) => {
  await page.getByTestId("create-folder-button").click();
  await page.getByTestId("create-folder-input").click();
  await page.getByTestId("create-folder-input").fill(folderName);
  await page.getByRole("button", { name: "Create" }).click();
  const folderItem = await getRowItem(page, folderName);
  await expect(folderItem).toBeVisible();
  return folderItem;
};

export const deleteCurrentFolder = async (page: Page) => {
  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  await expect(breadcrumbs).toBeVisible();
  const lastBreadcrumbButton = breadcrumbs
    .getByTestId("breadcrumb-button")
    .last();
  await lastBreadcrumbButton.click();
  await page.getByRole("menuitem", { name: "Delete" }).click();
};
