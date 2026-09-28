import path from "path";
import test, { expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { getRowItem } from "./utils-embedded-grid";
import { uploadFile } from "./utils/upload-utils";
import { grantClipboardPermissions } from "./utils/various-utils";

const IMAGE_FILE_PATH = path.join(__dirname, "/assets/test-image.png");
const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

const injectConvertAbility = (item: Record<string, unknown>) => {
  item.abilities = {
    ...(item.abilities as Record<string, unknown>),
    convert: true,
  };
};

/**
 * Intercepts items API responses to inject convert: true on all items.
 */
const mockRequiresConversion = async (page: Page) => {
  await page.route(
    (url) => /\/api\/v1\.0\/items(\/|$)/.test(url.pathname),
    async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      const response = await route.fetch();
      const json = await response.json();
      if (Array.isArray(json?.results)) {
        json.results.forEach(injectConvertAbility);
      } else if (json?.id) {
        injectConvertAbility(json);
      }
      await route.fulfill({ response, json });
    },
  );
};

test("Double-clicking a file with convert ability opens the conversion modal", async ({
  page,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  await clearDb();
  await login(page, "drive@example.com");
  await mockRequiresConversion(page);
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  await uploadFile(page, DOCX_FILE_PATH);
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  const row = await getRowItem(page, "empty_doc");
  await row.dblclick();

  await expect(
    page.getByRole("dialog", { name: "Convert to open this file" }),
  ).toBeVisible();
});

test("Cancelling the conversion modal (convert mocked) does not call the convert API", async ({
  page,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  await clearDb();
  await login(page, "drive@example.com");
  await mockRequiresConversion(page);
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  await uploadFile(page, DOCX_FILE_PATH);
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  let convertCalled = false;
  await page.route("**/api/v1.0/items/*/convert/", async (route) => {
    convertCalled = true;
    await route.continue();
  });

  const row = await getRowItem(page, "empty_doc");
  await row.dblclick();
  await expect(
    page.getByRole("dialog", { name: "Convert to open this file" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(
    page.getByRole("dialog", { name: "Convert to open this file" }),
  ).not.toBeVisible();
  expect(convertCalled).toBe(false);
});

test("Confirming the conversion modal (convert mocked) shows the converting placeholder in the folder", async ({
  page,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  await clearDb();
  await login(page, "drive@example.com");
  await mockRequiresConversion(page);
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  await uploadFile(page, DOCX_FILE_PATH);
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  // The POST /convert/ now returns the placeholder Item directly. We mock it
  // and let the front-end refresh the folder so the placeholder appears.
  const placeholderId = "00000000-0000-0000-0000-000000000001";
  await page.route("**/api/v1.0/items/*/convert/", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: placeholderId,
        title: "empty_doc.docx",
        filename: "empty_doc.docx",
        type: "file",
        upload_state: "converting",
        abilities: {},
      }),
    });
  });

  const placeholder = {
    id: placeholderId,
    title: "empty_doc.docx",
    filename: "empty_doc.docx",
    type: "file",
    upload_state: "converting",
    abilities: {},
  };

  // Inject the placeholder in the folder list returned by /items/ so it shows
  // up after the post-conversion refresh. This route shadows the one set by
  // mockRequiresConversion, so it must re-inject the convert ability too.
  await page.route(
    (url) => /\/api\/v1\.0\/items(\/|$)/.test(url.pathname),
    async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      const response = await route.fetch();
      const json = await response.json();
      if (Array.isArray(json?.results)) {
        json.results.forEach(injectConvertAbility);
        json.results.push(placeholder);
      } else if (json?.id) {
        injectConvertAbility(json);
      }
      await route.fulfill({ response, json });
    },
  );

  // The poller GETs the placeholder right away: keep it in the converting
  // state so the placeholder row stays in the folder.
  await page.route(`**/api/v1.0/items/${placeholderId}/`, async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(placeholder),
    });
  });

  const row = await getRowItem(page, "empty_doc");
  await row.dblclick();
  await expect(
    page.getByRole("dialog", { name: "Convert to open this file" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Convert" }).click();

  await expect(
    page.getByRole("dialog", { name: "Convert to open this file" }),
  ).not.toBeVisible({ timeout: 5000 });
  // The grid renders a hidden duplicate of each row (drag ghost), hence the
  // visibility filter.
  await expect(
    page.getByText("conversion in progress").filter({ visible: true }),
  ).toBeVisible();

  // Ignore routes still fetching when the test ends.
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("Conversion failure removes the converting placeholder and shows an error toast", async ({
  page,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  await clearDb();
  await login(page, "drive@example.com");
  await mockRequiresConversion(page);
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  await uploadFile(page, DOCX_FILE_PATH);
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  const placeholderId = "00000000-0000-0000-0000-000000000001";
  await page.route("**/api/v1.0/items/*/convert/", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: placeholderId,
        title: "empty_doc.docx",
        filename: "empty_doc.docx",
        type: "file",
        upload_state: "converting",
        abilities: {},
      }),
    });
  });

  // Inject the placeholder in the folder list returned by /items/. This route
  // shadows the one set by mockRequiresConversion, so it must re-inject the
  // convert ability too.
  await page.route(
    (url) => /\/api\/v1\.0\/items(\/|$)/.test(url.pathname),
    async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      const response = await route.fetch();
      const json = await response.json();
      const placeholder = {
        id: placeholderId,
        title: "empty_doc.docx",
        filename: "empty_doc.docx",
        type: "file",
        upload_state: "converting",
        abilities: {},
      };
      if (Array.isArray(json?.results)) {
        json.results.forEach(injectConvertAbility);
        json.results.push(placeholder);
      } else if (json?.id) {
        injectConvertAbility(json);
      }
      await route.fulfill({ response, json });
    },
  );

  // The poller's GET on the placeholder returns 404 (cleanup by the task on_failure).
  await page.route(
    `**/api/v1.0/items/${placeholderId}/`,
    async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not found." }),
      });
    },
  );

  const row = await getRowItem(page, "empty_doc");
  await row.dblclick();
  await expect(
    page.getByRole("dialog", { name: "Convert to open this file" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Convert" }).click();

  await expect(
    page.getByText("Conversion failed. Please try again."),
  ).toBeVisible({ timeout: 10000 });
  await expect(
    page.getByText("conversion in progress").filter({ visible: true }),
  ).not.toBeVisible({
    timeout: 10000,
  });

  // Ignore routes still fetching when the test ends.
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("Double-clicking a WOPI file opens the editor in a new tab", async ({
  page,
  context,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  await uploadFile(page, DOCX_FILE_PATH);
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  const row = await getRowItem(page, "empty_doc");
  const [wopiPage] = await Promise.all([
    context.waitForEvent("page"),
    row.dblclick(),
  ]);
  await wopiPage.waitForLoadState("domcontentloaded");

  // The preview modal must not open in the main tab.
  await expect(page.getByTestId("file-preview")).not.toBeVisible();

  const wopiIframe = wopiPage.locator('iframe[name="office_frame"]');
  await expect(wopiIframe).toBeVisible();
});

test("Navigating the previewer onto a WOPI file shows the Open in editor placeholder", async ({
  page,
  context,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  await uploadFile(page, [IMAGE_FILE_PATH, DOCX_FILE_PATH]);
  await expect(
    page.getByRole("cell", { name: "test-image", exact: true }),
  ).toBeVisible({ timeout: 10000 });
  await expect(
    page.getByRole("cell", { name: "empty_doc", exact: true }),
  ).toBeVisible({ timeout: 10000 });

  // Open a non-WOPI file first so the previewer mounts normally.
  await page
    .getByRole("cell", { name: "test-image", exact: true })
    .dblclick();
  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible({ timeout: 10000 });

  // Default ordering is "-type,title": empty_doc.docx sorts before
  // test-image.png, so ArrowLeft navigates from the image to the docx.
  await page.keyboard.press("ArrowLeft");

  const unsupported = filePreview.locator(".preview-message");
  await expect(unsupported).toBeVisible();
  await expect(
    unsupported.locator(".preview-message__title"),
  ).toHaveText("empty_doc.docx");

  const openButton = unsupported.getByRole("button", {
    name: "Open in editor",
  });
  await expect(openButton).toBeVisible();

  const [wopiPage] = await Promise.all([
    context.waitForEvent("page"),
    openButton.click(),
  ]);
  await wopiPage.waitForLoadState("domcontentloaded");

  await expect(wopiPage.locator('iframe[name="office_frame"]')).toBeVisible();
});

test("Copy and paste works in wopi editor", async ({
  page,
  context,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  grantClipboardPermissions(browserName, context);
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  //   Start waiting for file chooser before clicking. Note no await.
  await uploadFile(page, DOCX_FILE_PATH);

  // Wait for the file to be uploaded and visible in the list
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  // Double-click opens the editor in a new tab.
  const row = await getRowItem(page, "empty_doc");
  const [wopiPage] = await Promise.all([
    context.waitForEvent("page"),
    row.dblclick(),
  ]);
  await wopiPage.waitForLoadState("domcontentloaded");

  const wopiIframe = wopiPage.locator('iframe[name="office_frame"]');
  await expect(wopiIframe).toBeVisible();

  await expect(
    wopiPage
      .locator('iframe[name="office_frame"]')
      .contentFrame()
      .locator('iframe[name="iframe-welcome-form"]')
      .contentFrame()
      .getByRole("heading", { name: "Explore The New" }),
  ).toBeVisible({ timeout: 30000 });

  await wopiPage
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator('iframe[name="iframe-welcome-form"]')
    .contentFrame()
    .getByRole("button", { name: "Close" })
    .click();

  const canvas = wopiPage
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator('canvas[id="document-canvas"]');
  await expect(canvas).toBeVisible();

  // The editor zone is a canvas, so we need to take a screenshot of it.
  await expect(canvas).toHaveScreenshot("empty-doc-canvas.png", {
    maxDiffPixelRatio: 0.01,
  });
  await wopiPage
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator(".leaflet-layer")
    .click({ force: true });
  await wopiPage.waitForTimeout(1000);
  await wopiPage
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator("#clipboard-area")
    .press("ControlOrMeta+a");
  await wopiPage.waitForTimeout(1000);
  await wopiPage.keyboard.press(`ControlOrMeta+KeyC`);
  await wopiPage.waitForTimeout(1000);
  await wopiPage
    .locator('iframe[name="office_frame"]')
    .contentFrame()
    .locator("#clipboard-area")
    .press("ArrowRight");
  await wopiPage.waitForTimeout(1000);
  await wopiPage.keyboard.press(`ControlOrMeta+KeyV`);
  await wopiPage.waitForTimeout(1000);
  await expect(canvas).toHaveScreenshot("empty-doc-canvas-after-paste.png", {
    maxDiffPixelRatio: 0.01,
  });
});
