import test, { expect } from "@playwright/test";
import path from "path";
import { clearDb, login } from "../app-drive/utils-common";
import { clickToMyFiles } from "../app-drive/utils-navigate";
import { uploadFile } from "../app-drive/utils/upload-utils";

const PDF_FILE_PATH = path.join(__dirname, "../app-drive/assets/pv_cm.pdf");

const SDK_CONSUMER_URL = "http://localhost:5173/";

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
});
