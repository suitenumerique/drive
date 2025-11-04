import { expect, Page } from "@playwright/test";
import { getItemTree, openTreeNode } from "./utils-tree";

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
