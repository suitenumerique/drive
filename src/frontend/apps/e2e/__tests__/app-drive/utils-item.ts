import { expect, Page } from "@playwright/test";
import { getRowItem } from "./utils-embedded-grid";

export const createFolder = async (page: Page, folderName: string) => {
  await page.getByRole("button", { name: "New folder" }).click();
  await page.getByRole("textbox", { name: "Folder name" }).click();
  await page.getByRole("textbox", { name: "Folder name" }).fill(folderName);
  await page.getByRole("button", { name: "Create" }).click();
};

export const createFolderInCurrentFolder = async (
  page: Page,
  folderName: string,
) => {
  await page.getByTestId("create-folder-button").click();
  await page.getByTestId("create-folder-input").click();
  await page.getByTestId("create-folder-input").fill(folderName);
  await page.getByRole("button", { name: "Create" }).click();
  const folderItem = await getRowItem(page, folderName);
  await expect(folderItem).toBeVisible();
  return folderItem;
};

// Exact match: the "New folder" button's accessible name also contains "New".
export const getNewButton = (page: Page) =>
  page.getByRole("button", { name: "New", exact: true });

export const createFileFromTemplate = async (
  page: Page,
  fileName: string,
  template: "New text document" | "New spreadsheet" | "New slides" = "New text document",
) => {
  await getNewButton(page).click();
  await page.getByRole("menuitem", { name: template }).click();
  await page.getByRole("textbox", { name: "File name" }).fill(fileName);
  await page.getByRole("button", { name: "Create" }).click();
  const fileItem = await getRowItem(page, fileName);
  await expect(fileItem).toBeVisible();
  return fileItem;
};

export const importFile = async (page: Page, filePath: string) => {
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Import" }).click();
  await page.getByRole("menuitem", { name: "Import files" }).click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(filePath);
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
