import test, { expect } from "@playwright/test";
import { getStorageState } from "./utils-common";

test.use({ storageState: getStorageState("drive") });

test("Create a folder", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Drop your files here")).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "My first folder" })
  ).not.toBeVisible();
  await page.getByRole("button", { name: "add Create" }).click();
  await page.getByText("New folder").click();
  await page
    .getByRole("textbox", { name: "Folder name" })
    .fill("My first folder");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByText("Drop your files here")).not.toBeVisible();
  await expect(
    page.getByRole("cell", { name: "My first folder" })
  ).toBeVisible();
  await page.getByRole("cell", { name: "few seconds ago" }).click();
});
