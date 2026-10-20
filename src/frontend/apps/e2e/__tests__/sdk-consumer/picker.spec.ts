import test, { expect } from "@playwright/test";
import path from "path";
import { clearDb, login } from "../app-drive/utils-common";
import { clickToMyFiles } from "../app-drive/utils-navigate";
import { uploadFile } from "../app-drive/utils/upload-utils";

const PDF_FILE_PATH = path.join(__dirname, "../app-drive/assets/pv_cm.pdf");

const SDK_CONSUMER_URL = "http://localhost:5173/";

const API_URL = "http://localhost:8071/api/v1.0";

// Replaces the expiration of the given item wherever it shows in a response.
const withLinkExpiresAt = (
  value: unknown,
  itemId: string,
  linkExpiresAt: string,
): unknown => {
  if (Array.isArray(value)) {
    return value.map((entry) =>
      withLinkExpiresAt(entry, itemId, linkExpiresAt),
    );
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value).map(([key, entry]) => [
      key,
      withLinkExpiresAt(entry, itemId, linkExpiresAt),
    ]);
    const result = Object.fromEntries(entries);
    return result.id === itemId
      ? { ...result, link_expires_at: linkExpiresAt }
      : result;
  }
  return value;
};

test.describe("SDK file picker", () => {
  test.beforeEach(async () => {
    await clearDb();
  });

  test("cancel the picker, consumer shows cancelled and file stays private", async ({
    page,
  }) => {
    // 1. Log in and upload a file in the drive app.
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
    await expect(page.getByText("This tab is empty")).toBeVisible();

    await uploadFile(page, PDF_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    // 2. Go to the SDK consumer app and open the picker.
    await page.goto(SDK_CONSUMER_URL);
    const popupPromise = page.waitForEvent("popup");
    await page.getByRole("button", { name: "Open picker" }).click();
    const picker = await popupPromise;
    await picker.waitForLoadState("domcontentloaded");

    // 3. Select the file, then cancel instead of confirming — this proves
    // cancel aborts even an in-progress selection.
    const fileRow = picker.locator("tr", { hasText: "pv_cm" });
    await expect(fileRow).toBeVisible({ timeout: 15000 });
    await fileRow.click();

    const cancelButton = picker.getByRole("button", {
      name: "Cancel",
      exact: true,
    });
    await expect(cancelButton).toBeEnabled();
    await cancelButton.click();

    await picker.waitForEvent("close");

    // 4. Consumer shows the cancelled state, not the selection list.
    await expect(
      page.getByRole("heading", { name: "Cancelled :(" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Selected items:" }),
    ).not.toBeVisible();

    // 5. The item's link_reach must NOT have been promoted to public by
    // a cancel — fetch it via the authenticated search endpoint (the
    // root items list only returns top-level workspaces).
    const searchRes = await page.request.get(
      "http://localhost:8071/api/v1.0/items/search/?q=pv_cm",
    );
    expect(searchRes.ok()).toBeTruthy();
    const body = await searchRes.json();
    const items = Array.isArray(body) ? body : body.results;
    const uploaded = items.find(
      (it: { title: string }) => it.title === "pv_cm.pdf",
    );
    expect(uploaded, "uploaded file not returned by search").toBeTruthy();
    expect(uploaded.link_reach).not.toBe("public");
  });

  test("pick a file, see it selected, and its URL is publicly reachable", async ({
    page,
    browser,
  }) => {
    // 1. Log in and upload a file in the drive app.
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
    await expect(page.getByText("This tab is empty")).toBeVisible();

    await uploadFile(page, PDF_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    // 2. Go to the SDK consumer app.
    await page.goto(SDK_CONSUMER_URL);
    await expect(
      page.getByRole("button", { name: "Open picker" }),
    ).toBeVisible();

    // 3. Click "Open picker" and capture the popup.
    const popupPromise = page.waitForEvent("popup");
    await page.getByRole("button", { name: "Open picker" }).click();
    const picker = await popupPromise;
    await picker.waitForLoadState("domcontentloaded");

    // 4. Select the file in the picker and confirm.
    const fileRow = picker.locator("tr", { hasText: "pv_cm" });
    await expect(fileRow).toBeVisible({ timeout: 15000 });
    await fileRow.click();

    const chooseButton = picker.getByRole("button", {
      name: "Choose",
      exact: true,
    });
    await expect(chooseButton).toBeEnabled();
    await chooseButton.click();

    // Popup closes itself after the selection event is sent.
    await picker.waitForEvent("close");

    // 5. Consumer displays "Selected items:" with the picked file.
    await expect(
      page.getByRole("heading", { name: "Selected items:" }),
    ).toBeVisible();

    const selectedLink = page.locator("ul a", { hasText: /./ }).first();
    await expect(selectedLink).toBeVisible();
    const publicUrl = await selectedLink.getAttribute("href");
    expect(publicUrl).toBeTruthy();

    await expect(page.getByText("pv_cm.pdf")).toBeVisible();

    // 6. The URL must be reachable in a fresh context (no auth cookies).
    // We open it in a real page so the step is visible in headed mode.
    // The backend serves it with Content-Disposition: attachment, so goto
    // rejects with "Download is starting" — we instead wait for the
    // download event, which only fires when the file actually streams.
    const anonContext = await browser.newContext();
    try {
      const anonPage = await anonContext.newPage();
      const downloadPromise = anonPage.waitForEvent("download");
      await anonPage.goto(publicUrl!).catch(() => {
        // Expected: navigation aborts because the response is a download.
      });
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/pv_cm/);
    } finally {
      await anonContext.close();
    }
  });

  test("pick an expired public file, its link is opened again", async ({
    page,
  }) => {
    // 1. Log in, upload a file and make its link public until next week.
    await login(page, "drive@example.com");
    await page.goto("/");
    await clickToMyFiles(page);
    await uploadFile(page, PDF_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "pv_cm", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    const searchRes = await page.request.get(
      `${API_URL}/items/search/?q=pv_cm`,
    );
    const body = await searchRes.json();
    const items = Array.isArray(body) ? body : body.results;
    const fileId = items.find(
      (it: { title: string }) => it.title === "pv_cm.pdf",
    ).id;
    const csrf = (await page.context().cookies(API_URL)).find(
      (cookie) => cookie.name === "csrftoken",
    )!.value;
    const inOneWeek = new Date(Date.now() + 7 * 24 * 3600 * 1000);
    const configured = await page.request.put(
      `${API_URL}/items/${fileId}/link-configuration/`,
      {
        data: {
          link_reach: "public",
          link_role: "reader",
          link_expires_at: inOneWeek.toISOString(),
        },
        headers: { "X-CSRFToken": csrf },
      },
    );
    expect(configured.ok()).toBeTruthy();

    // 2. Serve the file as the backend does once its link has expired: the
    // reach stays public with a past date. The backend refuses past dates, so
    // the picker listings are faked.
    const itemsUrl = "**/api/v1.0/items/**";
    await page.context().route(itemsUrl, async (route) => {
      if (route.request().method() !== "GET") {
        return route.fallback();
      }
      const response = await route.fetch();
      const json = await response.json().catch(() => undefined);
      if (json === undefined) {
        return route.fulfill({ response });
      }
      await route.fulfill({
        response,
        json: withLinkExpiresAt(json, fileId, "2020-01-01T00:00:00Z"),
      });
    });

    // 3. Pick the file from the SDK consumer.
    await page.goto(SDK_CONSUMER_URL);
    const popupPromise = page.waitForEvent("popup");
    await page.getByRole("button", { name: "Open picker" }).click();
    const picker = await popupPromise;
    await picker.waitForLoadState("domcontentloaded");
    const fileRow = picker.locator("tr", { hasText: "pv_cm" });
    await expect(fileRow).toBeVisible({ timeout: 15000 });
    await fileRow.click();

    // 4. Its reach is already public, but the picker must still update the
    // link and clear the past date, otherwise the link stays closed.
    const linkConfiguration = picker.waitForRequest(
      (request) =>
        request.url().includes(`/items/${fileId}/link-configuration/`) &&
        request.method() === "PUT",
    );
    await picker.getByRole("button", { name: "Choose", exact: true }).click();
    expect((await linkConfiguration).postDataJSON()).toMatchObject({
      link_reach: "public",
      link_expires_at: null,
    });
    await expect(
      page.getByRole("heading", { name: "Selected items:" }),
    ).toBeVisible();

    // 5. The backend no longer holds an expiration for the file.
    await page.context().unroute(itemsUrl);
    const item = await page.request.get(`${API_URL}/items/${fileId}/`);
    expect((await item.json()).link_expires_at).toBeNull();
  });
});
