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
  extraConfig: Record<string, unknown> = {},
) => {
  await page.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    if (helpMenuConfig === undefined) {
      delete json.FRONTEND_HELP_MENU_CONFIG;
    } else {
      json.FRONTEND_HELP_MENU_CONFIG = helpMenuConfig;
    }
    Object.assign(json, extraConfig);
    await route.fulfill({ response, json });
  });
};

// Records window.open calls so that mailto links can be asserted without
// relying on the browser actually opening them.
const spyOnWindowOpen = async (page: import("@playwright/test").Page) => {
  await page.addInitScript(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__openedUrls = [];
    window.open = (url?: string | URL) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__openedUrls.push(String(url));
      return null;
    };
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

  test("opens the support email when clicking on contact us", async ({
    page,
  }) => {
    await overrideHelpMenuConfig(page, HELP_MENU_CONFIG);
    await spyOnWindowOpen(page);
    await login(page, "drive@example.com");
    await page.goto("/");

    const footer = page.locator(".c__left-panel__footer__drive");
    await footer.getByRole("button", { name: "Help" }).click();
    await page.getByRole("menuitem", { name: "Contact us" }).click();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const openedUrls = await page.evaluate(() => (window as any).__openedUrls);
    expect(openedUrls).toEqual([HELP_MENU_CONFIG.supportEmail]);
  });

  test("opens the messages widget when clicking on contact us", async ({
    page,
  }) => {
    const widgetPath = "https://widget.example.com/";
    await overrideHelpMenuConfig(
      page,
      {
        ...HELP_MENU_CONFIG,
        supportMessagesWidget: true,
      },
      {
        FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL: "https://widget.example.com/api/",
        FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH: widgetPath,
        FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL: "drive",
      },
    );
    // Serve an empty widget script so the injected loader does not hit the
    // network for real.
    await page.route(`${widgetPath}feedback.js`, (route) =>
      route.fulfill({ contentType: "application/javascript", body: "" }),
    );
    await spyOnWindowOpen(page);
    await login(page, "drive@example.com");
    await page.goto("/");

    const footer = page.locator(".c__left-panel__footer__drive");
    await footer.getByRole("button", { name: "Help" }).click();
    await page.getByRole("menuitem", { name: "Contact us" }).click();

    // The widget queues an init call and injects its loader script.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const widgetCalls = await page.evaluate(() => (window as any)._stmsg_widget);
    expect(widgetCalls).toHaveLength(1);
    expect(widgetCalls[0][0]).toBe("feedback");
    expect(widgetCalls[0][1]).toBe("init");
    expect(widgetCalls[0][2].channel).toBe("drive");
    await expect(
      page.locator(`script[src="${widgetPath}feedback.js"]`),
    ).toHaveCount(1);

    // The widget takes precedence over the support email.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const openedUrls = await page.evaluate(() => (window as any).__openedUrls);
    expect(openedUrls).toEqual([]);
  });

  test("shows the messages widget button on the homepage when configured", async ({
    page,
  }) => {
    const widgetPath = "https://widget.example.com/";
    await overrideHelpMenuConfig(page, HELP_MENU_CONFIG, {
      FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL: "https://widget.example.com/api/",
      FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH: widgetPath,
      FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL: "drive",
    });
    // Serve an empty loader script so the injected loader does not hit the
    // network for real.
    await page.route(`${widgetPath}loader.js`, (route) =>
      route.fulfill({ contentType: "application/javascript", body: "" }),
    );
    // No login: the home page only renders for anonymous users, and it is
    // where the widget button is shown.
    await page.goto("/");

    // The button loader queues an init call and injects its loader script.
    await expect(
      page.locator(`script[src="${widgetPath}loader.js"]`),
    ).toHaveCount(1);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const widgetCalls = await page.evaluate(() => (window as any)._stmsg_widget);
    expect(widgetCalls).toHaveLength(1);
    expect(widgetCalls[0][0]).toBe("loader");
    expect(widgetCalls[0][1]).toBe("init");
    expect(widgetCalls[0][2].params.channel).toBe("drive");
    expect(widgetCalls[0][2].script).toBe(`${widgetPath}feedback.js`);
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

// The form itself (validation, anti-spam check, request shape) is tested in
// the UI kit. These tests check how Drive configures and opens it.
test.describe("Help menu - La Suite support form", () => {
  // Same origin as the app, so the requests can be stubbed without CORS.
  const SUPPORT_API = "/test-support-api/";

  const openContactUs = async (page: import("@playwright/test").Page) => {
    const footer = page.locator(".c__left-panel__footer__drive");
    await footer.getByRole("button", { name: "Help" }).click();
    await page.getByRole("menuitem", { name: "Contact us" }).click();
  };

  test("opens the support form instead of the support email", async ({
    page,
  }) => {
    // 1. Configure both the support email and the support form.
    await overrideHelpMenuConfig(page, {
      ...HELP_MENU_CONFIG,
      laSuiteSupportForm: { api: SUPPORT_API, channel: "fichiers" },
    });
    await spyOnWindowOpen(page);
    await login(page, "drive@example.com");
    await page.goto("/");

    // 2. "Contact us" opens the form, and the email link is not opened.
    await openContactUs(page);
    await expect(
      page.getByRole("dialog", { name: "Contact the team" }),
    ).toBeVisible();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const openedUrls = await page.evaluate(() => (window as any).__openedUrls);
    expect(openedUrls).toEqual([]);

    // 3. The user is logged in: Drive passes their email, so the form does
    //    not ask for it.
    await expect(page.getByRole("textbox", { name: "E-mail" })).toHaveCount(0);
  });

  test("sends the message to the configured API and channel", async ({
    page,
  }) => {
    // 1. Stub the support API. The challenge is a cheap SHA-256 one with a
    //    one-byte prefix, solved in milliseconds: the real anti-spam check is
    //    tested in the UI kit.
    await overrideHelpMenuConfig(page, {
      ...HELP_MENU_CONFIG,
      laSuiteSupportForm: { api: SUPPORT_API, channel: "fichiers" },
    });
    await page.route(`**${SUPPORT_API}challenge`, (route) =>
      route.fulfill({
        json: {
          parameters: {
            algorithm: "SHA-256",
            cost: 1,
            keyLength: 32,
            keyPrefix: "00",
            nonce: "00",
            salt: "00",
          },
          signature: "test",
        },
      }),
    );
    // Record the delivered request to check what Drive sends.
    const deliverRequest = page.waitForRequest(`**${SUPPORT_API}deliver/`);
    await page.route(`**${SUPPORT_API}deliver/`, (route) =>
      route.fulfill({ json: { success: true } }),
    );
    await login(page, "drive@example.com");
    await page.goto("/");

    // 2. Fill the form and send it.
    await openContactUs(page);
    await page.getByRole("textbox", { name: "Subject" }).fill("Upload issue");
    await page
      .getByRole("textbox", { name: "Your message" })
      .fill("The upload button does nothing.");
    await page.getByRole("button", { name: "Send" }).click();

    // 3. The request carries Drive's channel and the user's email, and the
    //    form shows its success view.
    const request = await deliverRequest;
    expect(request.headers()["x-channel-id"]).toBe("fichiers");
    expect(request.postDataJSON()).toMatchObject({
      subject: "Upload issue",
      textBody: "The upload button does nothing.",
      email: "drive@example.com",
      channel: "fichiers",
    });
    await expect(
      page.getByRole("heading", { name: "Thank you for your feedback" }),
    ).toBeVisible();
  });

  test("keeps the support email when the form config has no channel", async ({
    page,
  }) => {
    // 1. A partial form config: the API without the channel.
    await overrideHelpMenuConfig(page, {
      ...HELP_MENU_CONFIG,
      laSuiteSupportForm: { api: SUPPORT_API },
    });
    await spyOnWindowOpen(page);
    await login(page, "drive@example.com");
    await page.goto("/");

    // 2. "Contact us" falls back to the support email instead of opening a
    //    form that could not send.
    await openContactUs(page);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const openedUrls = await page.evaluate(() => (window as any).__openedUrls);
    expect(openedUrls).toEqual([HELP_MENU_CONFIG.supportEmail]);
    await expect(page.getByRole("dialog", { name: "Contact the team" })).toHaveCount(0);
  });
});
