import { Page, Route, Locator, expect } from "@playwright/test";
import { login } from "../utils-common";
import { clickToMyFiles } from "../utils-navigate";

/**
 * Upload one or more files via the Import button and file chooser.
 */
export const uploadFile = async (page: Page, filePath: string | string[]) => {
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Import" }).click();
  await page.getByRole("menuitem", { name: "Import files" }).click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(filePath);
};

/**
 * Mock the config API response with a custom DATA_UPLOAD_MAX_MEMORY_SIZE value.
 * Must be called before page.goto() so the intercept is in place when the app loads.
 */
export const mockConfigWithUploadLimit = async (
  page: Page,
  maxMemorySize: number,
) => {
  await page.route("**/api/v1.0/config/", async (route: Route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.DATA_UPLOAD_MAX_MEMORY_SIZE = maxMemorySize;
    await route.fulfill({ response, json });
  });
};

/**
 * Common setup: login, mock config upload limit, navigate to My Files.
 */
export const setupUploadTest = async (
  page: Page,
  maxMemorySize: number = 10 * 1024 * 1024,
) => {
  await login(page, "drive@example.com");
  await mockConfigWithUploadLimit(page, maxMemorySize);
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();
};

// --- Toast locators ---

export const getUploadToast = (page: Page): Locator =>
  page.locator(".file-upload-toast");

export const getFileRow = (page: Page, fileName: string): Locator =>
  page
    .locator(".file-upload-toast__files__item")
    .filter({ hasText: fileName });

export const getFileRowErrorText = (
  page: Page,
  fileName: string,
): Locator =>
  getFileRow(page, fileName).locator(
    ".file-upload-toast__files__item__error-text",
  );

export const getFileRowCheckIcon = (
  page: Page,
  fileName: string,
): Locator =>
  getFileRow(page, fileName).locator(
    ".file-upload-toast__files__item__check",
  );

export const getToastDescriptionText = (page: Page): Locator =>
  page.locator(".file-upload-toast__description__text");

export const getToastErrorIndicator = (page: Page): Locator =>
  page.locator(".file-upload-toast__description__error-indicator");

export const getToastToggleButton = (page: Page): Locator =>
  page
    .locator(".file-upload-toast__description")
    .getByRole("button")
    .filter({ has: page.locator("span.material-icons", { hasText: /keyboard_arrow/ }) });

export const getToastCloseButton = (page: Page): Locator =>
  page
    .locator(".file-upload-toast__description")
    .getByRole("button")
    .filter({ has: page.locator("span.material-icons", { hasText: "close" }) });

export const getFilesList = (page: Page): Locator =>
  page.locator(".file-upload-toast__files");

/**
 * Mock a slow upload by intercepting PUT requests to S3/minio.
 * Returns a resolve function to unblock the upload.
 */
export const mockSlowUpload = async (
  page: Page,
): Promise<{ resolve: () => void }> => {
  let resolveUpload: () => void;
  const uploadPromise = new Promise<void>((resolve) => {
    resolveUpload = resolve;
  });

  await page.route(/.*s3.*|.*minio.*/, async (route) => {
    if (route.request().method() === "PUT") {
      await uploadPromise;
      await route.continue();
    } else {
      await route.continue();
    }
  });

  return { resolve: () => resolveUpload!() };
};

/**
 * Mock a slow upload-ended by intercepting POST requests to the upload-ended endpoint.
 * The S3 upload proceeds normally, but the upload-ended call is blocked until resolve() is called.
 * Returns a resolve function to unblock the upload-ended call.
 */
export const mockSlowUploadEnded = async (
  page: Page,
): Promise<{ resolve: () => void }> => {
  let resolveUploadEnded: () => void;
  const uploadEndedPromise = new Promise<void>((resolve) => {
    resolveUploadEnded = resolve;
  });

  await page.route("**/api/v1.0/items/*/upload-ended/", async (route) => {
    await uploadEndedPromise;
    await route.continue();
  });

  return { resolve: () => resolveUploadEnded!() };
};
