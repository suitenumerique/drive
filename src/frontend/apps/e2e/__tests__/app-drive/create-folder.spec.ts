import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";

test("Create a folder", async ({ page }) => {
  await clearDb();
  await login(page, "drive@example.com");

  await page.goto("/");
  await expect(page.getByText("This tab is empty")).toBeVisible();
  await expect(page.getByText("Import or create files and")).toBeVisible();
  await page.getByRole("button", { name: "Create Folder" }).click();

  await page
    .getByRole("textbox", { name: "Folder name" })
    .fill("My first folder");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByText("Drop your files here")).not.toBeVisible();
  await expect(
    page.getByRole("cell", { name: "My first folder", exact: true })
  ).toBeVisible();
  await page.getByRole("cell", { name: "few seconds ago" }).click();
});
