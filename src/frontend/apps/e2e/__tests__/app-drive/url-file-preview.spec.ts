import test, { expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import path from "path";
import { clickToMyFiles } from "./utils-navigate";
import { uploadFile } from "./utils/upload-utils";
import { grantClipboardPermissions } from "./utils/various-utils";
import { clickCopyLinkButton, selectLinkReach } from "./utils/share-utils";

const PDF_PATH = path.join(__dirname, "/assets/pv_cm.pdf");
const PDF_NAME = "pv_cm.pdf";

export const setLinkReachAndCopyLink = async (
  page: Page,
  linkReach: string,
) => {
  await selectLinkReach(page, linkReach);
  await clickCopyLinkButton(page);
  await expect(page.getByText("Copied to clipboard")).toBeVisible();
  const handle = await page.evaluateHandle(() =>
    navigator.clipboard.readText(),
  );
  return (await handle.jsonValue()) as string;
};

const uploadFileAndCopyPublicLink = async (page: Page): Promise<string> => {
  await uploadFile(page, PDF_PATH);
  await expect(page.getByText("This tab is empty")).not.toBeVisible();
  await page
    .getByRole("button", { name: `More actions for ${PDF_NAME}` })
    .nth(1)
    .click({ force: true });
  await page.getByRole("menuitem", { name: "Share" }).click();
  return setLinkReachAndCopyLink(page, "Public");
};

test("Share url leads to standalone file preview", async ({
  page,
  context,
  browserName,
}) => {
  // On the CI the evaluateHandle is not working with webkit.
  if (browserName === "webkit") {
    return;
  }
  grantClipboardPermissions(browserName, context);
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  //   Start waiting for file chooser before clicking. Note no await.
  await uploadFile(page, path.join(__dirname, "/assets/pv_cm.pdf"));

  await expect(page.getByText("This tab is empty")).not.toBeVisible();
  await page
    .getByRole("button", { name: "More actions for pv_cm.pdf" })
    .nth(1)
    .click({ force: true });
  await page.getByRole("menuitem", { name: "Share" }).click();
  await page.getByRole("button", { name: "link Copy link" }).click();
  await expect(page.getByText("Copied to clipboard")).toBeVisible();

  // Get clipboard content after the link/button has been clicked
  const handle = await page.evaluateHandle(() =>
    navigator.clipboard.readText(),
  );
  const clipboardContent = await handle.jsonValue();
  await page.goto(clipboardContent);

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();
  await expect(filePreview.getByText("pv_cm")).toBeVisible();
  await expect(
    filePreview
      .getByTestId("file-preview")
      .getByRole("button", { name: "close" }),
  ).not.toBeVisible();
  await expect(filePreview.getByTestId("file-preview-nav")).not.toBeVisible();
});

test("Wrong url leads to 404 instead of standalone file preview", async ({
  page,
}) => {
  await login(page, "drive@example.com");
  // This uuid is valid but does not exist in the database.
  await page.goto(
    "http://localhost:3000/explorer/items/files/c36ee34b-56c8-460b-b5fc-22245c5a3da4",
  );

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).not.toBeVisible();

  await page.getByText("The file you are looking for").click();
});

test("Public file preview — authenticated user sees MyFilesCTA", async ({
  page,
  context,
  browserName,
}) => {
  if (browserName === "webkit") {
    return;
  }
  grantClipboardPermissions(browserName, context);
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  const fileUrl = await uploadFileAndCopyPublicLink(page);
  await page.goto(fileUrl);

  await expect(page.getByTestId("file-preview")).toBeVisible();
  await expect(page.getByTestId("my-files-cta")).toBeVisible();
  await expect(page.getByTestId("anonymous-cta-login")).not.toBeVisible();
  await expect(page.getByTestId("anonymous-cta-try-out")).not.toBeVisible();

  await page.getByTestId("my-files-cta").click();
  await page.waitForURL("**/explorer/items/my-files");
  expect(new URL(page.url()).pathname).toBe("/explorer/items/my-files");
});

test("Public file preview — anonymous user sees AnonymousCTA", async ({
  page,
  context,
  browser,
  browserName,
}) => {
  if (browserName === "webkit") {
    return;
  }
  grantClipboardPermissions(browserName, context);
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  const fileUrl = await uploadFileAndCopyPublicLink(page);

  const anonContext = await browser.newContext();
  const anonPage = await anonContext.newPage();
  await anonPage.goto(fileUrl);

  await expect(anonPage.getByTestId("file-preview")).toBeVisible();
  await expect(anonPage.getByTestId("anonymous-cta-login")).toBeVisible();
  await expect(anonPage.getByTestId("anonymous-cta-try-out")).toBeVisible();
  await expect(anonPage.getByTestId("my-files-cta")).not.toBeVisible();

  // Default fallback: try-out points to "/"
  await expect(anonPage.getByTestId("anonymous-cta-try-out")).toHaveAttribute(
    "href",
    "/",
  );
  await anonPage.getByTestId("anonymous-cta-try-out").click();
  await anonPage.waitForURL((url) => url.pathname === "/");

  // Reload preview to test the login button.
  await anonPage.goto(fileUrl);
  await expect(anonPage.getByTestId("anonymous-cta-login")).toBeVisible();
  await Promise.all([
    anonPage.waitForRequest((req) => req.url().includes("/authenticate/")),
    anonPage.getByTestId("anonymous-cta-login").click(),
  ]);

  await anonContext.close();
});

test("Public file preview — anonymous get redirected to FRONTEND_EXTERNAL_HOME_URL when clicking on try-out", async ({
  page,
  context,
  browser,
  browserName,
}) => {
  if (browserName === "webkit") {
    return;
  }
  grantClipboardPermissions(browserName, context);
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await expect(page.getByText("This tab is empty")).toBeVisible();

  const fileUrl = await uploadFileAndCopyPublicLink(page);

  const TRY_OUT_URL = "https://try-out.example.test/";
  const anonContext = await browser.newContext();
  const anonPage = await anonContext.newPage();
  await anonPage.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.FRONTEND_EXTERNAL_HOME_URL = TRY_OUT_URL;
    await route.fulfill({ response, json });
  });
  await anonPage.goto(fileUrl);

  await expect(anonPage.getByTestId("file-preview")).toBeVisible();
  await expect(anonPage.getByTestId("anonymous-cta-try-out")).toBeVisible();
  await expect(anonPage.getByTestId("anonymous-cta-try-out")).toHaveAttribute(
    "href",
    TRY_OUT_URL,
  );
  await expect(anonPage.getByTestId("anonymous-cta-login")).toBeVisible();
  await expect(anonPage.getByTestId("my-files-cta")).not.toBeVisible();

  await anonContext.close();
});
