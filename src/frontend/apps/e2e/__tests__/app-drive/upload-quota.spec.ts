import { expect, Page, test } from "@playwright/test";
import { login, runFixture } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";

const API = "http://localhost:8071/api/v1.0";

const post = async (page: Page, url: string, data?: unknown) => {
  const csrf = (await page.context().cookies(API)).find(
    (cookie) => cookie.name === "csrftoken",
  );
  return page.request.post(url, {
    data,
    headers: { "X-CSRFToken": csrf?.value ?? "" },
  });
};

test.describe("Upload reservations with real object storage", () => {
  test.beforeEach(async ({ page }) => {
    await runFixture("e2e_fixture_upload_quota");
    await login(page, "upload-quota@example.com");
    await page.route("**/api/v1.0/config/", async (route) => {
      const response = await route.fetch();
      const config = await response.json();
      config.FRONTEND_RELEASE_NOTE_ENABLED = false;
      delete config.FRONTEND_ENTITLEMENTS_DISCLAIMERS;
      await route.fulfill({ response, json: config });
    });
    await page.goto("/");
    await expect(
      page.getByRole("link", { name: "My files", exact: true }),
    ).toBeVisible();
  });

  test("reserves before PUT and finalizes without double counting", async ({
    page,
  }) => {
    await page.goto("/");
    await clickToMyFiles(page);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route(
      (url) => url.searchParams.has("X-Amz-Signature"),
      async (route) => {
        if (route.request().method() === "PUT") await gate;
        await route.continue();
      },
    );
    const creation = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        /\/items\/(?:[^/]+\/children\/)?$/.test(
          new URL(response.url()).pathname,
        ),
    );
    const chooser = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Import", exact: true }).click();
    await page
      .getByRole("menuitem", { name: "Import files", exact: true })
      .click();
    await (
      await chooser
    ).setFiles({
      name: "quota-reserved.txt",
      mimeType: "text/plain",
      buffer: Buffer.alloc(1023, "a"),
    });
    try {
      const response = await creation;
      expect(response.status()).toBe(201);
      expect(response.request().postDataJSON().expected_size).toBe(1023);
      const { id, policy } = await response.json();
      expect(new URL(policy).searchParams.get("X-Amz-SignedHeaders")).toContain(
        "content-length",
      );
      const quota = await (
        await page.request.get(`${API}/entitlements/`)
      ).json();
      expect(quota.quota).toMatchObject({ usage: 1023, limit: 1024 });
      const finalized = page.waitForResponse(
        `${API}/items/${id}/upload-ended/`,
      );
      release();
      expect((await finalized).status()).toBe(200);
      await expect(
        page.locator(".file-upload-toast__description__text"),
      ).toContainText("1 file transferred");
      await expect(
        page.getByRole("cell", { name: "quota-reserved", exact: true }),
      ).toBeVisible();
      expect(
        (await (await page.request.get(`${API}/entitlements/`)).json()).quota
          .usage,
      ).toBe(1023);
      expect(
        (await post(page, `${API}/items/${id}/upload-ended/`)).status(),
      ).toBe(200);
    } finally {
      release();
    }
  });

  test("MinIO rejects a body larger than the signed reservation", async ({
    page,
  }) => {
    const response = await post(page, `${API}/items/`, {
      type: "file",
      filename: "bounded.txt",
      expected_size: 8,
    });
    expect(response.status()).toBe(201);
    const { policy } = await response.json();
    const config = await (await page.request.get(`${API}/config/`)).json();
    const headers: Record<string, string> = { "Content-Type": "text/plain" };
    if (config.AWS_S3_UPLOAD_ACL && config.AWS_S3_UPLOAD_ACL !== "default") {
      headers["x-amz-acl"] = config.AWS_S3_UPLOAD_ACL;
    }
    const oversized = await page.request.put(policy, {
      data: Buffer.alloc(9, "a"),
      headers,
    });
    expect(oversized.status()).toBe(403);
    expect(await oversized.text()).toContain("SignatureDoesNotMatch");
    const valid = await page.request.put(policy, {
      data: Buffer.alloc(8, "a"),
      headers,
    });
    expect(valid.status()).toBe(200);
    // Deliberately omit upload-ended: these bytes must still count.
    expect(
      (await (await page.request.get(`${API}/entitlements/`)).json()).quota
        .usage,
    ).toBe(8);
  });

  test("cached quota allows a temporary overshoot then blocks new reservations", async ({
    page,
  }) => {
    const first = await post(page, `${API}/items/`, {
      type: "file",
      filename: "first.txt",
      expected_size: 600,
    });
    expect(first.status()).toBe(201);
    // Warm the existing cache below the quota, then reuse that permission.
    expect(
      (await (await page.request.get(`${API}/entitlements/`)).json()).quota
        .usage,
    ).toBe(600);
    const second = await post(page, `${API}/items/`, {
      type: "file",
      filename: "second.txt",
      expected_size: 600,
    });
    expect(second.status()).toBe(201);
    // The committed creation invalidates the cache. Both pending uploads now count.
    expect(
      (await (await page.request.get(`${API}/entitlements/`)).json()).quota
        .usage,
    ).toBe(1200);
    const rejected = await post(page, `${API}/items/`, {
      type: "file",
      filename: "refused.txt",
      expected_size: 1,
    });
    expect(rejected.status()).toBe(403);
    expect((await rejected.json()).errors[0].code).toBe(
      "user_override_quota_exceeded",
    );
    expect(
      (await (await page.request.get(`${API}/entitlements/`)).json()).quota
        .usage,
    ).toBe(1200);
  });

  test("empty files use a signed zero-byte PUT", async ({ page }) => {
    await page.goto("/");
    await clickToMyFiles(page);
    const chooser = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Import", exact: true }).click();
    await page
      .getByRole("menuitem", { name: "Import files", exact: true })
      .click();
    await (
      await chooser
    ).setFiles({
      name: "zero.txt",
      mimeType: "text/plain",
      buffer: Buffer.alloc(0),
    });
    await expect(
      page.locator(".file-upload-toast__description__text"),
    ).toContainText("1 file transferred");
    await expect(
      page.getByRole("cell", { name: "zero", exact: true }),
    ).toBeVisible();
    expect(
      (await (await page.request.get(`${API}/entitlements/`)).json()).quota
        .usage,
    ).toBe(0);
  });
});
