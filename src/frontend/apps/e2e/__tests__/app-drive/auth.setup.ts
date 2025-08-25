import { expect, Page, test as setup } from "@playwright/test";

import { getStorageState, keyCloakSignIn } from "./utils-common";

const login = async (page: Page, username: string, password: string) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.content();

  await keyCloakSignIn(page, username, password);

  await expect(
    page.getByRole("button", {
      name: "My Account",
    })
  ).toBeVisible({ timeout: 10000 });

  await page.context().storageState({
    path: getStorageState(username),
  });
};

setup("authenticate as drive", async ({ page }) => {
  await login(page, "drive", "drive");
});
