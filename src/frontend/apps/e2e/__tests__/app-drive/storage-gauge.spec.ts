import { expect, Page, test } from "@playwright/test";
import path from "path";
import { login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { uploadFile } from "./utils/upload-utils";

type QuotaPayload = {
  state: "default" | "excedeed_locked" | "error";
  reason?: string;
  error?: string;
  usage?: number;
  limit?: number;
};

type EntitlementsPayload = {
  can_access: { result: boolean };
  can_upload: { result: boolean; reason?: string | null };
  context: Record<string, unknown>;
  quota?: QuotaPayload;
};

const ENTITLEMENTS_URL = "**/api/v1.0/entitlements/";
const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

const DEFAULT_QUOTA: QuotaPayload = {
  state: "default",
  usage: 1_500_000_000,
  limit: 10_000_000_000,
};

const baseEntitlements = (quota?: QuotaPayload): EntitlementsPayload => ({
  can_access: { result: true },
  can_upload: { result: true, reason: null },
  context: {},
  ...(quota ? { quota } : {}),
});

const mockEntitlements = async (page: Page, payload: EntitlementsPayload) => {
  await page.route(ENTITLEMENTS_URL, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    });
  });
};

/**
 * Patch the real config response. The cannot_upload disclaimer modal is always
 * disabled so it never overlaps the gauge, and the storage gauge information
 * link is set or removed depending on the scenario.
 */
const mockConfig = async (page: Page, storageGaugeLink?: string) => {
  await page.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    delete json.FRONTEND_ENTITLEMENTS_DISCLAIMERS;
    if (storageGaugeLink === undefined) {
      delete json.FRONTEND_STORAGE_GAUGE_INFORMATION_LINK;
    } else {
      json.FRONTEND_STORAGE_GAUGE_INFORMATION_LINK = storageGaugeLink;
    }
    await route.fulfill({ response, json });
  });
};

/**
 * Navigate and wait for the entitlements request to complete.
 * `/entitlements/` fires from `useEntitlements` once the user is loaded.
 */
const goAndWaitForEntitlements = async (page: Page) => {
  const entitlementsResponse = page.waitForResponse(ENTITLEMENTS_URL);
  await page.goto("/");
  await entitlementsResponse;
};

const REACT_RENDER_GRACE_MS = 300;

const getGaugeButton = (page: Page) => page.locator("button.c__storage-gauge");
const getGaugeLabel = (page: Page) =>
  page.locator(".c__storage-gauge__label").first();
const getGaugeFill = (page: Page) =>
  page.locator(".c__storage-gauge .c__storage-gauge__bar__fill");
const getGaugeInformation = (page: Page) =>
  page.locator(".c__storage-gauge__information");

const openSettingsModal = async (page: Page) => {
  await getGaugeButton(page).click();
  await expect(getGaugeInformation(page)).toBeVisible();
};

test.describe("StorageGauge", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "drive@example.com");
  });

  test.describe("Gauge button states", () => {
    test("is hidden when entitlements have no quota", async ({ page }) => {
      await mockConfig(page);
      await mockEntitlements(page, baseEntitlements());

      await goAndWaitForEntitlements(page);
      // Grace period so the negative assertion does not pass trivially
      // during the React render gap following the entitlements response.
      await page.waitForTimeout(REACT_RENDER_GRACE_MS);
      await expect(getGaugeButton(page)).not.toBeVisible();
    });

    test("shows usage and limit in the default state", async ({ page }) => {
      await mockConfig(page);
      await mockEntitlements(page, baseEntitlements(DEFAULT_QUOTA));

      await goAndWaitForEntitlements(page);
      await expect(getGaugeButton(page)).toBeVisible();
      await expect(getGaugeLabel(page)).toHaveText("1.50 / 10 Go");
      await expect(getGaugeFill(page)).toHaveAttribute("style", /width: 15%/);
    });

    test("fills the bar accordingly above the 80% warning threshold", async ({
      page,
    }) => {
      await mockConfig(page);
      await mockEntitlements(
        page,
        baseEntitlements({
          state: "default",
          usage: 8_500_000_000,
          limit: 10_000_000_000,
        }),
      );

      await goAndWaitForEntitlements(page);
      await expect(getGaugeLabel(page)).toHaveText("8.50 / 10 Go");
      await expect(getGaugeFill(page)).toHaveAttribute("style", /width: 85%/);
    });

    test("caps the bar at 100% when usage exceeds the limit", async ({
      page,
    }) => {
      await mockConfig(page);
      await mockEntitlements(
        page,
        baseEntitlements({
          state: "default",
          usage: 12_000_000_000,
          limit: 10_000_000_000,
        }),
      );

      await goAndWaitForEntitlements(page);
      await expect(getGaugeLabel(page)).toHaveText("12.00 / 10 Go");
      await expect(getGaugeFill(page)).toHaveAttribute("style", /width: 100%/);
    });

    test("is locked when the organization quota is exceeded", async ({
      page,
    }) => {
      await mockConfig(page);
      await mockEntitlements(
        page,
        baseEntitlements({
          state: "excedeed_locked",
          reason: "organization_quota_excedeed",
        }),
      );

      await goAndWaitForEntitlements(page);
      await expect(getGaugeButton(page)).toBeVisible();
      await expect(getGaugeButton(page)).toHaveClass(
        /c__storage-gauge--locked/,
      );
      await expect(
        getGaugeButton(page).getByText("Org. quota exceeded"),
      ).toBeVisible();
      await expect(getGaugeLabel(page)).not.toBeVisible();
    });

    for (const error of [
      "metric_account_not_found",
      "max_storage_account_not_found",
    ]) {
      test(`is locked with an explanatory tooltip on error ${error}`, async ({
        page,
      }) => {
        await mockConfig(page);
        await mockEntitlements(
          page,
          baseEntitlements({ state: "error", error }),
        );

        await goAndWaitForEntitlements(page);
        await expect(getGaugeButton(page)).toBeVisible();
        await expect(getGaugeButton(page)).toHaveClass(
          /c__storage-gauge--locked/,
        );
        await expect(
          getGaugeButton(page).getByText("Quota error"),
        ).toBeVisible();

        // A first mouse move lets react-aria register the pointer modality;
        // hovering directly as the very first mouse interaction of the page
        // does not open the tooltip.
        await page.mouse.move(0, 0);
        await getGaugeButton(page).hover();
        await expect(page.locator(".c__tooltip__content")).toHaveText(
          `Error: ${error}`,
        );
      });
    }
  });

  test.describe("Settings modal", () => {
    test("shows the storage usage in the default state", async ({ page }) => {
      await mockConfig(page);
      await mockEntitlements(page, baseEntitlements(DEFAULT_QUOTA));

      await goAndWaitForEntitlements(page);
      await openSettingsModal(page);

      await expect(
        getGaugeInformation(page).getByText("Used Storage"),
      ).toBeVisible();
      await expect(
        getGaugeInformation(page).getByText("1.50 of 10 Go used"),
      ).toBeVisible();
    });

    test("explains how to unlock when the organization quota is exceeded", async ({
      page,
    }) => {
      await mockConfig(page);
      await mockEntitlements(
        page,
        baseEntitlements({
          state: "excedeed_locked",
          reason: "organization_quota_excedeed",
        }),
      );

      await goAndWaitForEntitlements(page);
      await openSettingsModal(page);

      await expect(
        getGaugeInformation(page).getByText("Organization quota exceeded"),
      ).toBeVisible();
      await expect(
        getGaugeInformation(page).getByText(
          "Contact an administrator to increase the quota",
        ),
      ).toBeVisible();
    });

    test("explains how to resolve the error state", async ({ page }) => {
      await mockConfig(page);
      await mockEntitlements(
        page,
        baseEntitlements({
          state: "error",
          error: "metric_account_not_found",
        }),
      );

      await goAndWaitForEntitlements(page);
      await openSettingsModal(page);

      await expect(
        getGaugeInformation(page).getByText("Quota error"),
      ).toBeVisible();
      await expect(
        getGaugeInformation(page).getByText(
          "Contact support to resolve the error",
        ),
      ).toBeVisible();
    });
  });

  test.describe("More info link", () => {
    const INFORMATION_LINK = "https://storage-info.example.test/help";

    test("opens the configured link in a new tab", async ({ page }) => {
      // Fulfill the external link so the popup does not depend on the network.
      await page.context().route(`${INFORMATION_LINK}*`, (route) =>
        route.fulfill({ status: 200, contentType: "text/html", body: "ok" }),
      );
      await mockConfig(page, INFORMATION_LINK);
      await mockEntitlements(page, baseEntitlements(DEFAULT_QUOTA));

      await goAndWaitForEntitlements(page);
      await openSettingsModal(page);

      const moreInfoButton = getGaugeInformation(page).getByRole("button", {
        name: "More info",
      });
      await expect(moreInfoButton).toBeVisible();

      const popupPromise = page.waitForEvent("popup");
      await moreInfoButton.click();
      const popup = await popupPromise;
      await popup.waitForLoadState("domcontentloaded");
      expect(popup.url()).toBe(INFORMATION_LINK);
    });

    test("is not rendered when the link is not configured", async ({
      page,
    }) => {
      await mockConfig(page);
      await mockEntitlements(page, baseEntitlements(DEFAULT_QUOTA));

      await goAndWaitForEntitlements(page);
      await openSettingsModal(page);

      await expect(
        getGaugeInformation(page).getByRole("button", { name: "More info" }),
      ).not.toBeVisible();
    });
  });

  test.describe("Refresh after upload", () => {
    test("updates the gauge once an upload has completed", async ({
      page,
    }) => {
      let usage = 1_500_000_000;
      await mockConfig(page);
      // The backend couples upload-ended to its own entitlements provider
      // (it may reject the upload server-side); fulfill it so the upload
      // flow completes regardless of the backend entitlements setup. The
      // response body is not used by the frontend.
      await page.route("**/api/v1.0/items/*/upload-ended/", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: "{}",
        }),
      );
      await page.route(ENTITLEMENTS_URL, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(
            baseEntitlements({
              state: "default",
              usage,
              limit: 10_000_000_000,
            }),
          ),
        });
      });

      await goAndWaitForEntitlements(page);
      await expect(getGaugeLabel(page)).toHaveText("1.50 / 10 Go");

      await clickToMyFiles(page);
      // The next entitlements fetch reports the post-upload usage.
      usage = 2_500_000_000;
      await uploadFile(page, DOCX_FILE_PATH);

      // Entitlements are refetched once the upload queue drains.
      await expect(getGaugeLabel(page)).toHaveText("2.50 / 10 Go", {
        timeout: 15_000,
      });
    });
  });
});
