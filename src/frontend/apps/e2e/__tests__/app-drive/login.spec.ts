import { expect, test as setup } from "@playwright/test";

import { keyCloakSignIn } from "./utils-common";

setup("authenticate as drive", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.content();

  await keyCloakSignIn(page, "drive", "drive");

  await expect(
    page.getByRole("button", {
      name: "My Account",
    })
  ).toBeVisible({ timeout: 10000 });
});
