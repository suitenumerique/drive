import { expect, Page, test } from "@playwright/test";
import { login } from "./utils-common";

type CannotUploadConfig = {
  enabled: boolean;
  showPotentialOperators?: boolean;
};

type PotentialOperator = {
  id: string;
  name: string;
  siret: string;
  url: string | null;
  config: Record<string, unknown>;
  signupUrl: string;
};

type EntitlementsPayload = {
  can_access: { result: boolean; reason?: string };
  can_upload: { result: boolean; reason?: string };
  context: {
    organization?: { id: string; type: string; name: string };
    potentialOperators?: PotentialOperator[];
  };
};

const SEEN_KEY = "entitlement-disclaimer-seen:cannot_upload";
const MODAL_TITLE = "Uploads are unavailable";
const NOT_ACTIVATED_DESCRIPTION =
  /File upload isn't activated for your organization/i;
const NO_ORGANIZATION_DESCRIPTION =
  /Your account isn't linked to an organization/i;
const POTENTIAL_OPERATORS_HEADER =
  /Here is the list of potential operators/i;
const ENTITLEMENTS_URL = "**/api/v1.0/entitlements/";

const DEFAULT_ENABLED_CONFIG: CannotUploadConfig = {
  enabled: true,
  showPotentialOperators: false,
};

const mockConfig = async (
  page: Page,
  cannotUpload: CannotUploadConfig | undefined,
) => {
  await page.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    if (cannotUpload === undefined) {
      delete json.FRONTEND_ENTITLEMENTS_DISCLAIMERS;
    } else {
      json.FRONTEND_ENTITLEMENTS_DISCLAIMERS = {
        cannot_upload: cannotUpload,
      };
    }
    await route.fulfill({ response, json });
  });
};

const mockEntitlements = async (page: Page, payload: EntitlementsPayload) => {
  await page.route(ENTITLEMENTS_URL, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    });
  });
};

const notActivatedEntitlements = (
  overrides: Partial<EntitlementsPayload> = {},
): EntitlementsPayload => ({
  can_access: { result: true },
  can_upload: { result: false, reason: "not_activated" },
  context: {},
  ...overrides,
});

/**
 * Navigate and wait for the entitlements request to complete.
 * `/entitlements/` fires from `useEntitlements` once the user is loaded,
 * which in dev mode can take longer than the default 5s assertion timeout.
 */
const goAndWaitForEntitlements = async (page: Page) => {
  const entitlementsResponse = page.waitForResponse(ENTITLEMENTS_URL);
  await page.goto("/");
  await entitlementsResponse;
};

/**
 * Assert an element is not visible, after allowing React enough time to
 * render a potential modal following the entitlements response. Without this
 * grace period, `.not.toBeVisible()` resolves on the first poll and can pass
 * trivially during the React render gap — masking regressions where the
 * component incorrectly decides to show the modal.
 */
const REACT_RENDER_GRACE_MS = 300;
const expectNotVisibleAfterDecision = async (
  page: Page,
  locator = page.getByText(MODAL_TITLE),
) => {
  await page.waitForTimeout(REACT_RENDER_GRACE_MS);
  await expect(locator).not.toBeVisible();
};

test.describe("EntitlementDisclaimers", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "drive@example.com");
  });

  test.describe("Visibility rules", () => {
    test("shows the modal when enabled and reason is not_activated", async ({
      page,
    }) => {
      await mockConfig(page, DEFAULT_ENABLED_CONFIG);
      await mockEntitlements(page, notActivatedEntitlements());

      await goAndWaitForEntitlements(page);
      await expect(page.getByText(MODAL_TITLE)).toBeVisible();
      await expect(page.getByText(NOT_ACTIVATED_DESCRIPTION)).toBeVisible();
    });

    test("shows the no_organization description when reason is no_organization", async ({
      page,
    }) => {
      await mockConfig(page, DEFAULT_ENABLED_CONFIG);
      await mockEntitlements(
        page,
        notActivatedEntitlements({
          can_upload: { result: false, reason: "no_organization" },
        }),
      );

      await goAndWaitForEntitlements(page);
      await expect(page.getByText(MODAL_TITLE)).toBeVisible();
      await expect(page.getByText(NO_ORGANIZATION_DESCRIPTION)).toBeVisible();
    });

    test("does NOT show the modal when FRONTEND_ENTITLEMENTS_DISCLAIMERS is absent", async ({
      page,
    }) => {
      await mockConfig(page, undefined);
      await mockEntitlements(page, notActivatedEntitlements());

      await goAndWaitForEntitlements(page);
      await expectNotVisibleAfterDecision(page);
    });

    test("does NOT show the modal when the cannot_upload disclaimer is disabled", async ({
      page,
    }) => {
      await mockConfig(page, { enabled: false });
      await mockEntitlements(page, notActivatedEntitlements());

      await goAndWaitForEntitlements(page);
      await expectNotVisibleAfterDecision(page);
    });

    test("does NOT show the modal when can_upload.result is true", async ({
      page,
    }) => {
      await mockConfig(page, DEFAULT_ENABLED_CONFIG);
      await mockEntitlements(
        page,
        notActivatedEntitlements({ can_upload: { result: true } }),
      );

      await goAndWaitForEntitlements(page);
      await expectNotVisibleAfterDecision(page);
    });

    test("does NOT show the modal when reason is outside the whitelist", async ({
      page,
    }) => {
      await mockConfig(page, DEFAULT_ENABLED_CONFIG);
      await mockEntitlements(
        page,
        notActivatedEntitlements({
          can_upload: { result: false, reason: "storage_full" },
        }),
      );

      await goAndWaitForEntitlements(page);
      await expectNotVisibleAfterDecision(page);
    });
  });

  test.describe("Seen / localStorage behavior", () => {
    test("is shown once, then hidden on the next load", async ({ page }) => {
      await mockConfig(page, DEFAULT_ENABLED_CONFIG);
      await mockEntitlements(page, notActivatedEntitlements());

      await goAndWaitForEntitlements(page);
      await expect(page.getByText(MODAL_TITLE)).toBeVisible();

      const flag = await page.evaluate(
        (key) => localStorage.getItem(key),
        SEEN_KEY,
      );
      expect(flag).toBe("1");

      const entitlementsAfterReload = page.waitForResponse(ENTITLEMENTS_URL);
      await page.reload();
      await entitlementsAfterReload;
      await expectNotVisibleAfterDecision(page);
    });

    test("clears the seen flag when entitlements no longer warrant the disclaimer", async ({
      page,
    }) => {
      await page.addInitScript((key) => {
        localStorage.setItem(key, "1");
      }, SEEN_KEY);

      await mockConfig(page, DEFAULT_ENABLED_CONFIG);
      await mockEntitlements(
        page,
        notActivatedEntitlements({ can_upload: { result: true } }),
      );

      await goAndWaitForEntitlements(page);
      await expectNotVisibleAfterDecision(page);

      await expect
        .poll(() =>
          page.evaluate((key) => localStorage.getItem(key), SEEN_KEY),
        )
        .toBeNull();
    });
  });

  test.describe("Potential operators", () => {
    const operators: PotentialOperator[] = [
      {
        id: "op-1",
        name: "Operator Alpha",
        siret: "11111111111111",
        url: null,
        config: {},
        signupUrl: "https://alpha.example.test/signup",
      },
      {
        id: "op-2",
        name: "Operator Beta",
        siret: "22222222222222",
        url: null,
        config: {},
        signupUrl: "",
      },
    ];

    test("does NOT render operators when showPotentialOperators is false", async ({
      page,
    }) => {
      await mockConfig(page, {
        enabled: true,
        showPotentialOperators: false,
      });
      await mockEntitlements(
        page,
        notActivatedEntitlements({
          context: { potentialOperators: operators },
        }),
      );

      await goAndWaitForEntitlements(page);
      await expect(page.getByText(MODAL_TITLE)).toBeVisible();
      await expect(
        page.getByText(POTENTIAL_OPERATORS_HEADER),
      ).not.toBeVisible();
      await expect(page.getByText("Operator Alpha")).not.toBeVisible();
    });

    test("renders operators and shows the register link only when signupUrl is set", async ({
      page,
    }) => {
      await mockConfig(page, {
        enabled: true,
        showPotentialOperators: true,
      });
      await mockEntitlements(
        page,
        notActivatedEntitlements({
          context: { potentialOperators: operators },
        }),
      );

      await goAndWaitForEntitlements(page);
      await expect(page.getByText(MODAL_TITLE)).toBeVisible();
      await expect(page.getByText(POTENTIAL_OPERATORS_HEADER)).toBeVisible();

      await expect(page.getByText("Operator Alpha")).toBeVisible();
      await expect(page.getByText("Operator Beta")).toBeVisible();

      const registerLinks = page.getByRole("link", { name: "Register" });
      await expect(registerLinks).toHaveCount(1);
      await expect(registerLinks).toHaveAttribute(
        "href",
        "https://alpha.example.test/signup",
      );
      await expect(registerLinks).toHaveAttribute("target", "_blank");
    });

    test("does NOT render the operators section when the list is empty", async ({
      page,
    }) => {
      await mockConfig(page, {
        enabled: true,
        showPotentialOperators: true,
      });
      await mockEntitlements(
        page,
        notActivatedEntitlements({
          context: { potentialOperators: [] },
        }),
      );

      await goAndWaitForEntitlements(page);
      await expect(page.getByText(MODAL_TITLE)).toBeVisible();
      await expect(
        page.getByText(POTENTIAL_OPERATORS_HEADER),
      ).not.toBeVisible();
    });
  });

  test.describe("Modal interaction", () => {
    test("closes when OK is clicked", async ({ page }) => {
      await mockConfig(page, DEFAULT_ENABLED_CONFIG);
      await mockEntitlements(page, notActivatedEntitlements());

      await goAndWaitForEntitlements(page);
      await expect(page.getByText(MODAL_TITLE)).toBeVisible();

      await page.getByRole("button", { name: "OK" }).click();
      await expect(page.getByText(MODAL_TITLE)).not.toBeVisible();
    });
  });
});
