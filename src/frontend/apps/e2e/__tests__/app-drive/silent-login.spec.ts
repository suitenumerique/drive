import test, { expect, Page, Route } from "@playwright/test";
import { keyCloakSignIn } from "./utils-common";

const SILENT_LOGIN_RETRY_KEY = "silent-login-retry";

/**
 * Helper to mock the config API response with custom FRONTEND_SILENT_LOGIN_ENABLED value
 */
const mockConfigApi = async (page: Page, silentLoginEnabled: boolean) => {
  await page.route("**/api/v1.0/config/", async (route: Route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.FRONTEND_SILENT_LOGIN_ENABLED = silentLoginEnabled;
    await route.fulfill({ response, json });
  });
};

/**
 * Helper to get the silent-login-retry value from localStorage
 */
const getSilentLoginRetryKey = async (page: Page): Promise<string | null> => {
  return page.evaluate((key) => localStorage.getItem(key), SILENT_LOGIN_RETRY_KEY);
};

/**
 * Helper to clear the silent-login-retry key from localStorage
 */
const clearSilentLoginRetryKey = async (page: Page) => {
  await page.evaluate((key) => localStorage.removeItem(key), SILENT_LOGIN_RETRY_KEY);
};

test.describe("Silent Login", () => {
  test("Silent login succeeds with active Keycloak session", async ({
    page,
    context,
  }) => {
    // Step 1: First login interactively via Keycloak
    await page.goto("/");
    await keyCloakSignIn(page, "drive", "drive");

    // Verify user is logged in
    await expect(
      page.getByRole("button", { name: "Open user menu" })
    ).toBeVisible({ timeout: 10000 });

    // Step 2: Clear only the Django session cookie (keep Keycloak session)
    const cookies = await context.cookies();
    const djangoSessionCookie = cookies.find(
      (cookie) => cookie.name === "drive_sessionid"
    );
    if (djangoSessionCookie) {
      await context.clearCookies({
        name: "drive_sessionid",
      });
    }

    // Clear localStorage retry key to allow silent login
    await clearSilentLoginRetryKey(page);

    // Step 3: Mock config API to enable silent login
    await mockConfigApi(page, true);

    // Step 4: Set up request interception to verify silent login redirect
    let silentLoginRequestMade = false;
    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("/authenticate/") && url.includes("silent=true")) {
        silentLoginRequestMade = true;
      }
    });

    // Step 5: Navigate to the app (use "commit" to handle redirect without ERR_ABORTED)
    await page.goto("/");

    // Step 6: Wait for the login page to be shown.
    // IMPORTANT: Ideally what we should test is that the user is automatically logged in, 
    // but we don't have a way to do that yet with the current setup as its seems that
    // Keycloak always returns a "login_failed" error when not running behind https.
    // So instead we just test that the redirect to the authenticate endpoint occurs with
    // silent=true.
    await expect(
      page.getByRole("button", { name: "Sign in" }).first()
    ).toBeVisible({ timeout: 10000 });

    // Step 7: Verify the silent login redirect occurred
    expect(silentLoginRequestMade).toBe(true);
  });

  test("Silent login fails gracefully without Keycloak session", async ({
    page,
    context,
  }) => {
    // Step 1: Ensure no session exists (clear all cookies)
    await context.clearCookies();

    // Step 2: Mock config API to enable silent login
    await mockConfigApi(page, true);

    // Step 3: Set up request interception to verify silent login redirect
    let silentLoginRequestMade = false;
    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("/authenticate/") && url.includes("silent=true")) {
        silentLoginRequestMade = true;
      }
    });

    // Step 4: Navigate to the app (use "commit" to handle redirect without ERR_ABORTED)
    await page.goto("/");

    // Step 5: Verify the login page is shown (no infinite redirect loop)
    await expect(
      page.getByRole("button", { name: "Sign in" }).first()
    ).toBeVisible({ timeout: 10000 });

    // Step 6: Verify the silent login redirect occurred
    expect(silentLoginRequestMade).toBe(true);

    // Step 7: Verify localStorage has the retry key set (preventing immediate retry)
    const retryKeyValue = await getSilentLoginRetryKey(page);
    expect(retryKeyValue).not.toBeNull();
  });

  test("Silent login disabled shows login page directly", async ({
    page,
    context,
  }) => {
    // Step 1: Ensure no session exists (clear all cookies)
    await context.clearCookies();

    // Step 2: Mock config API to disable silent login
    await mockConfigApi(page, false);

    // Step 3: Set up request interception to verify NO silent login redirect
    let silentLoginRequestMade = false;
    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("/authenticate/") && url.includes("silent=true")) {
        silentLoginRequestMade = true;
      }
    });

    // Step 4: Navigate to the app
    await page.goto("/");

    // Step 5: Verify the login page is shown directly
    await expect(
      page.getByRole("button", { name: "Sign in" }).first()
    ).toBeVisible({ timeout: 10000 });

    // Step 6: Verify no silent login redirect was attempted
    expect(silentLoginRequestMade).toBe(false);

    // Step 7: Verify no retry key in localStorage (silent login was never triggered)
    const retryKeyValue = await getSilentLoginRetryKey(page);
    expect(retryKeyValue).toBeNull();
  });

  test("No silent login redirect when user is already logged in", async ({
    page,
  }) => {
    // Step 1: Login interactively via Keycloak
    await page.goto("/");
    await keyCloakSignIn(page, "drive", "drive");

    // Step 2: Verify user is logged in
    await expect(
      page.getByRole("button", { name: "Open user menu" })
    ).toBeVisible({ timeout: 10000 });

    // Step 3: Mock config API to enable silent login
    await mockConfigApi(page, true);

    // Step 4: Set up request interception to verify NO silent login redirect
    let silentLoginRequestMade = false;
    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("/authenticate/") && url.includes("silent=true")) {
        silentLoginRequestMade = true;
      }
    });

    // Step 5: Navigate to the app again (simulating a page refresh or navigation)
    await page.goto("/");

    // Step 6: Verify user is still logged in (no redirect to login page)
    await expect(
      page.getByRole("button", { name: "Open user menu" })
    ).toBeVisible({ timeout: 10000 });

    // Step 7: Verify no silent login redirect was attempted
    expect(silentLoginRequestMade).toBe(false);
  });
});
