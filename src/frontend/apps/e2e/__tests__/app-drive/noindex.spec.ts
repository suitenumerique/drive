import { expect, test } from "@playwright/test";
import { login } from "./utils-common";

test.describe("Search engine indexing prevention", () => {
  test("should have noindex meta tag in head", async ({ page }) => {
    await login(page, "drive@example.com");
    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "User menu" }),
    ).toBeVisible();

    const robotsMeta = page.locator('meta[name="robots"][content="noindex"]');
    await expect(robotsMeta).toBeAttached();
  });

  test("should serve robots.txt that allows crawling", async ({ page }) => {
    // Crawling must stay allowed: crawlers can only honor the noindex
    // directive on pages they are able to fetch.
    const response = await page.request.get("/robots.txt");
    expect(response.status()).toBe(200);

    const content = await response.text();
    expect(content).toContain("User-agent: *");

    const rules = content
      .split("\n")
      .filter((line) => !line.startsWith("#"))
      .join("\n");
    expect(rules).not.toMatch(/Disallow: \//);
  });

  test("should serve pages with a X-Robots-Tag noindex header", async ({
    page,
  }) => {
    test.skip(
      !process.env.CI,
      "the header is added by nginx, not by the local dev server",
    );

    const response = await page.request.get("/");
    expect(response.headers()["x-robots-tag"]).toBe("noindex");
  });
});
