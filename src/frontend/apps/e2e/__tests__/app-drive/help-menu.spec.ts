import { expect, test } from "@playwright/test";
import { login } from "./utils-common";

const HELP_MENU_CONFIG = {
  documentationUrl: "https://example.com/docs",
  legal: {
    termsOfUseUrl: "https://example.com/tos",
  },
  supportEmail: "mailto:support@example.com",
};

const overrideHelpMenuConfig = async (
  page: import("@playwright/test").Page,
  helpMenuConfig: unknown,
) => {
  await page.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    if (helpMenuConfig === undefined) {
      delete json.FRONTEND_HELP_MENU_CONFIG;
    } else {
      json.FRONTEND_HELP_MENU_CONFIG = helpMenuConfig;
    }
    await route.fulfill({ response, json });
  });
};

test.describe("Help menu", () => {
  test("renders the help menu with the configured options", async ({
    page,
  }) => {
    await overrideHelpMenuConfig(page, HELP_MENU_CONFIG);
    await login(page, "drive@example.com");
    await page.goto("/");

    const footer = page.locator(".c__left-panel__footer__drive");
    await expect(footer).toBeVisible();

    await footer.getByRole("button", { name: "Help" }).click();

    await expect(page.getByRole("menuitem", { name: "Documentation" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Contact us" })).toBeVisible();
  });

  test("does not render the contact option when no support email is set", async ({
    page,
  }) => {
    await overrideHelpMenuConfig(page, {
      documentationUrl: HELP_MENU_CONFIG.documentationUrl,
    });
    await login(page, "drive@example.com");
    await page.goto("/");

    const footer = page.locator(".c__left-panel__footer__drive");
    await footer.getByRole("button", { name: "Help" }).click();

    await expect(page.getByRole("menuitem", { name: "Documentation" })).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Contact us" }),
    ).toHaveCount(0);
  });

  test("does not render the help menu when the config is empty", async ({
    page,
  }) => {
    await overrideHelpMenuConfig(page, {});
    await login(page, "drive@example.com");
    await page.goto("/");

    // The user menu confirms the layout has loaded before asserting absence.
    await expect(
      page.getByRole("button", { name: "User menu" }),
    ).toBeVisible();
    // The footer still renders (it hosts the storage gauge), but the help
    // menu button must not.
    const footer = page.locator(".c__left-panel__footer__drive");
    await expect(footer.getByRole("button", { name: "Help" })).toHaveCount(0);
  });
});
