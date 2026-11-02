import test, { expect, Page } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { expectRowItem } from "./utils-embedded-grid";
import { createFolderInCurrentFolder } from "./utils-item";
import { navigateToFolder } from "./utils-navigate";

test.describe("Create file from template", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
  });

  test("Create a text document (odt)", async ({ page }) => {
    await page.getByRole("button", { name: "New" }).click();
    await page.getByRole("menuitem", { name: "New text document" }).click();

    await page.getByRole("textbox", { name: "File name" }).fill("My document");
    await page.getByRole("button", { name: "Create" }).click();

    await expectRowItem(page, "My document");
  });

  test("Create a spreadsheet (ods)", async ({ page }) => {
    await page.getByRole("button", { name: "New" }).click();
    await page.getByRole("menuitem", { name: "New spreadsheet" }).click();

    await page
      .getByRole("textbox", { name: "File name" })
      .fill("My spreadsheet");
    await page.getByRole("button", { name: "Create" }).click();

    await expectRowItem(page, "My spreadsheet");
  });

  test("Create a presentation (odp)", async ({ page }) => {
    await page.getByRole("button", { name: "New" }).click();
    await page.getByRole("menuitem", { name: "New slides" }).click();

    await page
      .getByRole("textbox", { name: "File name" })
      .fill("My presentation");
    await page.getByRole("button", { name: "Create" }).click();

    await expectRowItem(page, "My presentation");
  });
});

test.describe("Create file from template in a folder", () => {
  test.beforeEach(async ({ page }) => {
    await clearDb();
    await login(page, "drive@example.com");
    await page.goto("/");
    await createFolderInCurrentFolder(page, "Test folder");
    await navigateToFolder(page, "Test folder", ["My files", "Test folder"]);
  });

  test("Create a text document (odt) in a folder", async ({ page }) => {
    await page.getByRole("button", { name: "New" }).click();
    await page.getByRole("menuitem", { name: "New text document" }).click();

    await page.getByRole("textbox", { name: "File name" }).fill("My document");
    await page.getByRole("button", { name: "Create" }).click();

    await expectRowItem(page, "My document");
  });

  test("Create a spreadsheet (ods) in a folder", async ({ page }) => {
    await page.getByRole("button", { name: "New" }).click();
    await page.getByRole("menuitem", { name: "New spreadsheet" }).click();

    await page
      .getByRole("textbox", { name: "File name" })
      .fill("My spreadsheet");
    await page.getByRole("button", { name: "Create" }).click();

    await expectRowItem(page, "My spreadsheet");
  });

  test("Create a presentation (odp) in a folder", async ({ page }) => {
    await page.getByRole("button", { name: "New" }).click();
    await page.getByRole("menuitem", { name: "New slides" }).click();

    await page
      .getByRole("textbox", { name: "File name" })
      .fill("My presentation");
    await page.getByRole("button", { name: "Create" }).click();

    await expectRowItem(page, "My presentation");
  });
});

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
    await page.getByRole("button", { name: "New" }).click();

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
    await page.getByRole("button", { name: "New" }).click();

    await expect(
      page.getByRole("menuitem", { name: "New folder" }),
    ).toBeEnabled();
  });
});
