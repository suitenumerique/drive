import test, { expect } from "@playwright/test";
import { clearDb, login } from "../utils-common";
import { clickOnRowItemActions, getRowItem } from "../utils-embedded-grid";

test("Check that the right content is displayed correctly", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await page.getByRole("button", { name: "add Create" }).click();
  await page.getByRole("menuitem", { name: "New folder" }).click();
  await page.getByRole("textbox", { name: "Folder name" }).fill("testFolder");
  await page.getByRole("button", { name: "Create" }).click();
  await getRowItem(page, "testFolder");
  await clickOnRowItemActions(page, "testFolder", "Info");
  const rightPanel = page.getByTestId("right-panel");
  await expect(rightPanel).toBeVisible();
  await expect(rightPanel.getByText("testFolder")).toBeVisible();
});
