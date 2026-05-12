import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  closeShareModal,
  openShareModal,
  selectLinkReach,
} from "./utils/share-utils";

test("Public folder — authenticated user does not see AnonymousCTA", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  await createFolderInCurrentFolder(page, "Public folder");
  await navigateToFolder(page, "Public folder", ["My files", "Public folder"]);
  await openShareModal(page);
  await selectLinkReach(page, "Public");
  await closeShareModal(page);

  await expect(page.getByTestId("anonymous-cta-login")).not.toBeVisible();
  await expect(page.getByTestId("anonymous-cta-try-out")).not.toBeVisible();
  await expect(page.getByTestId("anonymous-dropdown-menu")).not.toBeVisible();
});

test("Public folder — anonymous user sees AnonymousCTA and login redirects", async ({
  page,
  browser,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  await createFolderInCurrentFolder(page, "Public folder");
  await navigateToFolder(page, "Public folder", ["My files", "Public folder"]);
  await openShareModal(page);
  await selectLinkReach(page, "Public");
  await closeShareModal(page);
  const folderUrl = page.url();

  const anonContext = await browser.newContext();
  const anonPage = await anonContext.newPage();
  await anonPage.goto(folderUrl);

  await expect(anonPage.getByTestId("anonymous-cta-login")).toBeVisible();
  await expect(anonPage.getByTestId("my-files-cta")).not.toBeVisible();

  await Promise.all([
    anonPage.waitForRequest((req) => req.url().includes("/authenticate/")),
    anonPage.getByTestId("anonymous-cta-login").click(),
  ]);

  await anonContext.close();
});

test("Public folder — anonymous dropdown menu copies link and switches language", async ({
  page,
  browser,
  browserName,
}) => {
  // On the CI the evaluateHandle is not working with webkit.
  if (browserName === "webkit") {
    return;
  }
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);

  await createFolderInCurrentFolder(page, "Public folder");
  await navigateToFolder(page, "Public folder", ["My files", "Public folder"]);
  await openShareModal(page);
  await selectLinkReach(page, "Public");
  await closeShareModal(page);
  const folderUrl = page.url();

  const anonContext = await browser.newContext();
  await anonContext.grantPermissions(["clipboard-read", "clipboard-write"]);
  const anonPage = await anonContext.newPage();
  await anonPage.goto(folderUrl);

  // Dropdown trigger is visible for anonymous users.
  const dropdownTrigger = anonPage.getByTestId("anonymous-dropdown-menu");
  await expect(dropdownTrigger).toBeVisible();

  // Open the menu and verify both options are present.
  await dropdownTrigger.click();
  const copyLinkItem = anonPage.getByRole("menuitem", { name: "Copy link" });
  const languagesItem = anonPage.getByRole("menuitem", { name: "Languages" });
  await expect(copyLinkItem).toBeVisible();
  await expect(languagesItem).toBeVisible();

  // Copy link writes the current URL to the clipboard.
  await copyLinkItem.click();
  const handle = await anonPage.evaluateHandle(() =>
    navigator.clipboard.readText(),
  );
  expect(await handle.jsonValue()).toBe(folderUrl);

  // Languages submenu lists available languages and switches the UI language.
  await dropdownTrigger.click();
  await languagesItem.click();
  await expect(
    anonPage.getByRole("menuitem", { name: "Français" }),
  ).toBeVisible();
  await anonPage.getByRole("menuitem", { name: "Français" }).click();
  await expect(anonPage.getByTestId("anonymous-cta-login")).toHaveText(
    "Se connecter",
  );

  await anonContext.close();
});
