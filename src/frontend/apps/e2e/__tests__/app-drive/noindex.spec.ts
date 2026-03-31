import { expect, test } from "@playwright/test";
import { login } from "./utils-common";

test.describe("Search engine indexing prevention", () => {
  test("should have noindex meta tag in head", async ({ page }) => {
    await login(page, "drive@example.com");
    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "Open user menu" }),
    ).toBeVisible();

    const robotsMeta = page.locator('meta[name="robots"][content="noindex"]');
    await expect(robotsMeta).toBeAttached();
  });

  test("should serve robots.txt that disallows all crawlers", async ({
    page,
  }) => {
    const response = await page.request.get("/robots.txt");
    expect(response.status()).toBe(200);

    const content = await response.text();
    expect(content).toContain("User-agent: *");
    expect(content).toContain("Disallow: /");
  });
});
