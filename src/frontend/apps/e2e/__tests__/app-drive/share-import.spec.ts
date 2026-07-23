import { Page, expect, test } from "@playwright/test";
import path from "path";
import { clearDb, login } from "./utils-common";
import { createFolderInCurrentFolder } from "./utils-item";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";
import {
  expectUserInMembersList,
  getShareModal,
  openShareModal,
} from "./utils/share-utils";

const CONTACTS_CSV = path.join(__dirname, "assets/share-contacts.csv");

const mockConfig = async (page: Page, allowShareImportFile: boolean) => {
  await page.route("**/api/v1.0/config/", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.ALLOW_SHARE_IMPORT_FILE = allowShareImportFile;
    await route.fulfill({ response, json });
  });
};

const getImportModal = (page: Page) => {
  return page
    .locator(".c__modal")
    .filter({ has: page.locator(".c__share__import__modal") });
};

const openImportModal = async (page: Page) => {
  const shareModal = await openShareModal(page);
  await shareModal.getByRole("button", { name: "Import contacts" }).click();
  await page.getByRole("menuitem", { name: "Import contacts" }).click();
  const importModal = getImportModal(page);
  await expect(importModal).toBeVisible();
  return importModal;
};

const goToNewFolder = async (page: Page, folderName: string) => {
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, folderName);
  await navigateToFolder(page, folderName, ["My files", folderName]);
};

test.describe("Share modal contacts import", () => {
  test("the import entry is hidden when the feature is disabled", async ({
    page,
  }) => {
    await clearDb();
    await mockConfig(page, false);
    await login(page, "drive@example.com");
    await goToNewFolder(page, "Import disabled");

    const shareModal = await openShareModal(page);
    await expect(shareModal.getByTestId("members-list")).toBeVisible();
    await expect(
      shareModal.getByRole("button", { name: "Import contacts" }),
    ).toBeHidden();
  });

  test("importing a file shares with users and invites unknown emails", async ({
    page,
    request,
  }) => {
    await clearDb();
    // Make sure the webkit user exists so its row creates an access
    // while the unknown email creates an invitation.
    await request.post("http://localhost:8071/api/v1.0/e2e/user-auth/", {
      data: { email: "user@webkit.test" },
    });
    await mockConfig(page, true);
    await login(page, "drive@example.com");
    await goToNewFolder(page, "Import contacts folder");

    const importModal = await openImportModal(page);
    await importModal.locator('input[type="file"]').setInputFiles(CONTACTS_CSV);
    await expect(
      importModal.getByText("2 rows ready to be imported."),
    ).toBeVisible();
    await importModal.getByRole("button", { name: "Import", exact: true }).click();

    await expect(importModal).toBeHidden();
    await expectUserInMembersList(page, "user@webkit.test", "Editor");
    const shareModal = await getShareModal(page);
    await expect(shareModal.getByTestId("invitations-list")).toContainText(
      "imported@example.com",
    );
  });

  test("a failed import shows the backend error inside the import modal", async ({
    page,
  }) => {
    await clearDb();
    await mockConfig(page, true);
    await page.route("**/batch-share/", async (route) => {
      await route.fulfill({
        status: 400,
        json: {
          type: "validation_error",
          errors: [
            {
              attr: "rows",
              code: "invalid",
              detail: "This import is not valid.",
            },
          ],
        },
      });
    });
    await login(page, "drive@example.com");
    await goToNewFolder(page, "Import error folder");

    const importModal = await openImportModal(page);
    await importModal.locator('input[type="file"]').setInputFiles(CONTACTS_CSV);
    await importModal.getByRole("button", { name: "Import", exact: true }).click();

    await expect(
      importModal.getByText("This import is not valid."),
    ).toBeVisible();
    await expect(importModal).toBeVisible();

    // Removing the selected file clears the previous error
    await importModal.getByText("Delete", { exact: true }).first().click();
    await expect(
      importModal.getByText("This import is not valid."),
    ).toBeHidden();
  });
});
