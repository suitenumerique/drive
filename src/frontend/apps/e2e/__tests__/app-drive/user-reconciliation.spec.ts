import { expect, test } from "@playwright/test";

// A valid v4 UUID: the nginx rewrite serving the static export only matches
// v4 UUIDs (version "4", variant 8-b), like real reconciliation ids.
const FAKE_ID = "11111111-1111-4111-8111-111111111111";

test.describe("User reconciliation confirmation", () => {
  test("shows a success message when the backend confirms the email", async ({
    page,
  }) => {
    await page.route(
      "**/api/v1.0/user-reconciliations/active/**",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Confirmation received" }),
        });
      },
    );

    await page.goto(`/user-reconciliations/active/${FAKE_ID}/`);

    await expect(
      page.getByText("Your email address has been confirmed", { exact: false }),
    ).toBeVisible();
  });

  test("shows an error message when the backend rejects the confirmation", async ({
    page,
  }) => {
    await page.route(
      "**/api/v1.0/user-reconciliations/inactive/**",
      async (route) => {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Reconciliation entry not found" }),
        });
      },
    );

    await page.goto(`/user-reconciliations/inactive/${FAKE_ID}/`);

    await expect(
      page.getByText("An error occurred during email validation", {
        exact: false,
      }),
    ).toBeVisible();
  });
});
