import { expect, Page, test } from "@playwright/test";
import { login } from "./utils-common";

const mockSdkEnabled = async (page: Page, enabled: boolean) => {
  await page.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.SDK_ENABLED = enabled;
    await route.fulfill({ response, json });
  });
};

test.describe("SDK feature flag", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "drive@example.com");
  });

  test("should display a 404 on the sdk pages when SDK_ENABLED is false", async ({
    page,
  }) => {
    // 1. Disable the SDK through the config endpoint.
    await mockSdkEnabled(page, false);

    // 2. The entry page must render the 404 instead of storing the token and
    // redirecting to the picker.
    await page.goto("/sdk?token=test-token");
    await expect(page.getByText("This page could not be found")).toBeVisible();
    await expect(page).toHaveURL(/\/sdk\?token=test-token$/);

    // 3. The picker page must render the 404 too, even with a token already
    // stored, so the picker can't be reached directly.
    await page.evaluate(() =>
      sessionStorage.setItem("sdk_token", "test-token"),
    );
    await page.goto("/sdk/explorer");
    await expect(page.getByText("This page could not be found")).toBeVisible();
    await expect(page.getByText("Select one or more files")).not.toBeVisible();
  });

  test("should display the picker when SDK_ENABLED is true", async ({
    page,
  }) => {
    // 1. Enable the SDK through the config endpoint.
    await mockSdkEnabled(page, true);

    // 2. Going through the entry page stores the token and redirects to the
    // picker, which is displayed normally.
    await page.goto("/sdk?token=test-token");
    await expect(page).toHaveURL(/\/sdk\/explorer$/);
    await expect(page.getByText("Select one or more files")).toBeVisible();
    await expect(
      page.getByText("This page could not be found"),
    ).not.toBeVisible();
  });
});
