import test, { expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { expectRowItem } from "./utils-embedded-grid";
import {
  createFileFromTemplate,
  createFolderInCurrentFolder,
  getNewButton,
} from "./utils-item";
import { navigateToFolder } from "./utils-navigate";

const TEMPLATES = [
  {
    label: "a text document (odt)",
    fileName: "My document",
    template: "New text document",
  },
  {
    label: "a spreadsheet (ods)",
    fileName: "My spreadsheet",
    template: "New spreadsheet",
  },
  {
    label: "a presentation (odp)",
    fileName: "My presentation",
    template: "New slides",
  },
] as const;

const LOCATIONS = [
  { title: "Create file from template", suffix: "", openFolder: false },
  {
    title: "Create file from template in a folder",
    suffix: " in a folder",
    openFolder: true,
  },
];

for (const location of LOCATIONS) {
  test.describe(location.title, () => {
    test.beforeEach(async ({ page }) => {
      await clearDb();
      await login(page, "drive@example.com");
      await page.goto("/");
      if (location.openFolder) {
        await createFolderInCurrentFolder(page, "Test folder");
        await navigateToFolder(page, "Test folder", [
          "My files",
          "Test folder",
        ]);
      }
    });

    for (const { label, fileName, template } of TEMPLATES) {
      test(`Create ${label}${location.suffix}`, async ({ page }) => {
        await createFileFromTemplate(page, fileName, template);
        await expectRowItem(page, fileName);
      });
    }
  });
}

test.describe("Create file from template without the upload entitlement", () => {
  const mockEntitlements = async (page: Page) => {
    await page.route("**/api/v1.0/entitlements/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          can_access: { result: true },
          can_upload: { result: false, reason: "user_quota_exceeded" },
          context: {},
        }),
      });
    });
  };

  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await mockEntitlements(page);
    await page.goto("/");
  });

  test("disables the document entries and explains why", async ({ page }) => {
    await getNewButton(page).click();

    for (const name of ["New text document", "New spreadsheet", "New slides"]) {
      const entry = page.getByRole("menuitem", { name });
      await expect(entry).toBeVisible();
      await expect(entry).toBeDisabled();
    }

    await expect(
      page.getByText(/your personal quota has been reached/i).first(),
    ).toBeVisible();
  });

  test("keeps New folder available", async ({ page }) => {
    await getNewButton(page).click();

    await expect(
      page.getByRole("menuitem", { name: "New folder" }),
    ).toBeEnabled();
  });
});
