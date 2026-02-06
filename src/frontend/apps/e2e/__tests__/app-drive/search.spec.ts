import test, { expect } from "@playwright/test";
import { clearDb, login, runFixture } from "./utils-common";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import { clickToMyFiles } from "./utils-navigate";

test("Search somes items and shows them in the search modal", async ({
  page,
}) => {
  await clearDb();

  await runFixture("e2e_fixture_search");
  await login(page, "drive@example.com");

  await page.goto("/");

  await page.getByRole("button", { name: "Search" }).click();
  const input = page.getByRole("combobox", { name: "Quick search input" });
  await expect(input).toBeVisible();

  // Expect no results before typing.
  let searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(0);

  await input.fill("me");

  // Expect 3 results after typing "me".
  searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(3);

  let searchItem = page.getByRole("option", { name: "Meetings Dev Team" });
  await expect(searchItem).toContainText("Dev Team");

  searchItem = page.getByRole("option", {
    name: "Meeting notes 5th September",
  });
  await expect(searchItem).toContainText("Dev Team / Meetings");

  searchItem = page.getByRole("option", {
    name: "Meeting notes 15th September",
  });
  await expect(searchItem).toContainText("Dev Team / Meetings");

  await page.getByRole("combobox", { name: "Quick search input" }).fill("sale");

  searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(1);

  searchItem = page.getByRole("option", {
    name: "Sales report",
  });
  await expect(searchItem).toContainText("Project 2025");
});

test("Search folder and click on it", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);

  await page.getByRole("button", { name: "Search" }).click();

  const input = page.getByRole("combobox", { name: "Quick search input" });
  await expect(input).toBeVisible();
  await input.fill("meetings");

  const button = page.getByRole("option", { name: "Meetings" });
  await button.click();

  await expectExplorerBreadcrumbs(page, ["Dev Team", "Meetings"]);
});

test("Search file and click on it", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);
  await page.getByRole("button", { name: "Search" }).click();

  const input = page.getByRole("combobox", { name: "Quick search input" });
  await expect(input).toBeVisible();
  await input.fill("budget");

  const button = page.getByRole("option", { name: "Budget report" });
  await button.click();

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();
  await expect(filePreview.getByText("Budget report")).toBeVisible();
});

test("Search folder from trash and cannot navigate to it", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);

  await page.getByRole("button", { name: "Search" }).click();

  let searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(0);

  const input = page.getByRole("combobox", { name: "Quick search input" });
  await expect(input).toBeVisible();
  await input.fill("I am");

  // Set the scope to trash.
  await page.getByRole("button", { name: "Location" }).click();
  await page.getByRole("option", { name: "Recycle bin" }).click();

  searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(1);

  const button = page.getByRole("option", { name: "I am deleted" });
  await button.click();

  // We get a modal with a disclaimer.
  await expect(page.getByText("This folder is in the trash")).toBeVisible();
  await expect(
    page.getByText("To display this folder, you need to restore it first")
  ).toBeVisible();

  // Close the disclaimer modal.
  await page.getByRole("button", { name: "Ok" }).click();

  // The disclaimer modal is closed.
  await expect(page.getByText("This folder is in the trash")).not.toBeVisible();
  await expect(
    page.getByText("To display this folder, you need to restore it first")
  ).not.toBeVisible();
});

test("Search a deleted file and click on it", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await clickToMyFiles(page);
  await page.getByRole("button", { name: "Search" }).click();

  const input = page.getByRole("combobox", { name: "Quick search input" });
  await expect(input).toBeVisible();
  await input.fill("resum");

  // Set the scope to trash.
  await page.getByRole("button", { name: "Location" }).click();
  await page.getByRole("option", { name: "Recycle bin" }).click();

  let searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(1);

  const button = page.getByRole("option", { name: "Resume" });
  await button.click();

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();
  await expect(filePreview.getByText("Resume")).toBeVisible();
});
