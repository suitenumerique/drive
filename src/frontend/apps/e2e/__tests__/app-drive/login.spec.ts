import { expect, test as setup } from "@playwright/test";

import { oidcSignIn } from "./utils-common";

setup("authenticate as drive", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.content();

  await oidcSignIn(page, "drive@drive.world", "drive");

  await expect(
    page.getByRole("button", { name: "User menu" })
  ).toBeVisible({ timeout: 10000 });
});
