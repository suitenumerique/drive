import path from "path";
import test, { expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { getRowItem } from "./utils-embedded-grid";
import { uploadFile } from "./utils/upload-utils";
import { grantClipboardPermissions } from "./utils/various-utils";

const IMAGE_FILE_PATH = path.join(__dirname, "/assets/test-image.png");
const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

/**
 * Force every item returned by the items API to expose `wopi_actions:
 * ["convert"]`. This is the cheapest way to exercise the convert-confirmation
 * flow without depending on backend conversion heuristics.
 */
const mockWopiConvertAction = async (page: Page) => {
  const inject = (item: unknown) => {
    if (item && typeof item === "object") {
      (item as { wopi_actions?: string[] }).wopi_actions = ["convert"];
    }
  };
  await page.route(
    (url) => /\/api\/v1\.0\/items(\/|$)/.test(url.pathname),
    async (route) => {
      const response = await route.fetch();
      const contentType = response.headers()["content-type"] ?? "";
      if (!contentType.includes("application/json")) {
        await route.fulfill({ response });
        return;
      }
      try {
        const json = await response.json();
        if (Array.isArray(json?.results)) {
          json.results.forEach(inject);
        } else if (json && typeof json === "object") {
          inject(json);
        }
        await route.fulfill({ response, json });
      } catch {
        await route.fulfill({ response });
      }
    },
  );
};

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

test("Double-clicking a WOPI file with a convert action shows the confirmation modal", async ({
  page,
  context,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "Only runs on chromium");
  await clearDb();
  await login(page, "drive@example.com");
  await mockWopiConvertAction(page);
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  await uploadFile(page, DOCX_FILE_PATH);
  await expect(page.getByText("Drop your files here")).not.toBeVisible();

  const row = await getRowItem(page, "empty_doc");

  // Cancel branch: the modal opens and closes without spawning a new tab.
  await row.dblclick();
  const modalTitle = page.getByText("Convert to open this file");
  await expect(modalTitle).toBeVisible();

  let newTabOpened = false;
  const trackNewTab = (newPage: Page) => {
    if (newPage !== page) newTabOpened = true;
  };
  context.on("page", trackNewTab);

  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(modalTitle).not.toBeVisible();
  expect(newTabOpened).toBe(false);
  context.off("page", trackNewTab);

  // Confirm branch: clicking Convert opens the WOPI editor in a new tab.
  await row.dblclick();
  await expect(modalTitle).toBeVisible();

  const [wopiPage] = await Promise.all([
    context.waitForEvent("page"),
    page.getByRole("button", { name: "Convert" }).click(),
  ]);
  expect(wopiPage.url()).toContain("/wopi/");
  await expect(modalTitle).not.toBeVisible();
});
