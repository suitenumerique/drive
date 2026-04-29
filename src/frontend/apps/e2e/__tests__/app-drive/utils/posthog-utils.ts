import { expect, Page } from "@playwright/test";

const FAKE_POSTHOG_HOST = "http://fake-ph.test";

type CapturedEvent = {
  event: string;
  properties: Record<string, unknown>;
};

/**
 * Intercepts the config API to enable PostHog with a fake key and
 * captures all PostHog events sent by the page.
 *
 * Must be called **before** any page navigation (e.g. before `page.goto`).
 *
 * @returns An object with:
 *  - `events`: the live array of captured events with their properties
 *  - `expectEventSent(name, timeout?)`: polls until the given event name appears
 *  - `expectEventSentWithProps(name, props, timeout?)`: polls until at least
 *     one captured event matches the name AND has every entry in `props`
 *     as a strict equality match
 */
export const setupPosthogEventCapture = async (page: Page) => {
  const events: CapturedEvent[] = [];

  await page.route("**/api/v1.0/config/**", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.POSTHOG_KEY = "phc_fake_test_key";
    json.POSTHOG_HOST = FAKE_POSTHOG_HOST;
    await route.fulfill({ response, json });
  });

  await page.route(`${FAKE_POSTHOG_HOST}/**`, async (route) => {
    try {
      const postData = JSON.parse(route.request().postData() ?? "{}");
      if (postData.event) {
        events.push({
          event: postData.event,
          properties: postData.properties ?? {},
        });
      }
    } catch {
      // ignore non-JSON requests (e.g. /decide)
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "{}",
    });
  });

  const expectEventSent = async (eventName: string, timeout = 5000) => {
    await expect
      .poll(() => events.some((e) => e.event === eventName), { timeout })
      .toBe(true);
  };

  const expectEventSentWithProps = async (
    eventName: string,
    expectedProps: Record<string, unknown>,
    timeout = 5000,
  ) => {
    await expect
      .poll(
        () =>
          events.some(
            (e) =>
              e.event === eventName &&
              Object.entries(expectedProps).every(
                ([k, v]) => e.properties[k] === v,
              ),
          ),
        { timeout },
      )
      .toBe(true);
  };

  return { events, expectEventSent, expectEventSentWithProps };
};
