import test, { expect } from "@playwright/test";
import { clearDb, login } from "../utils-common";
import { clickOnRowItemActions, getRowItem } from "../utils-embedded-grid";
import { clickToMyFiles } from "../utils-navigate";
import { createFolderInCurrentFolder } from "../utils-item";

test("Check that the right content is displayed correctly", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "testFolder");
  await getRowItem(page, "testFolder");
  await clickOnRowItemActions(page, "testFolder", "Info");
  const rightPanel = page.getByTestId("right-panel");
  await expect(rightPanel).toBeVisible();
  await expect(rightPanel.getByText("testFolder")).toBeVisible();
});
