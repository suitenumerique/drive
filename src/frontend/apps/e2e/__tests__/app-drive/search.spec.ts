import test, { expect } from "@playwright/test";
import { clearDb, getStorageState, login, runFixture } from "./utils-common";
import { expectCurrentFolder } from "./utils-explorer";

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
  expect(searchItems).toHaveCount(3);

  await input.fill("me");

  // Expect 3 results after typing "me".
  searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(3);

  let searchItem = page.getByRole("button", { name: "Meetings Dev Team" });
  await expect(searchItem).toContainText("Dev Team");

  searchItem = page.getByRole("button", {
    name: "Meeting notes 5th September",
  });
  await expect(searchItem).toContainText("Dev Team / Meetings");

  searchItem = page.getByRole("button", {
    name: "Meeting notes 15th September",
  });
  await expect(searchItem).toContainText("Dev Team / Meetings");

  await page.getByRole("combobox", { name: "Quick search input" }).fill("sale");

  searchItems = page.getByTestId("search-item");
  expect(searchItems).toHaveCount(1);

  searchItem = page.getByRole("button", {
    name: "Sales report",
  });
  await expect(searchItem).toContainText("Project 2025");
});

test("Search folder and click on it", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await expectCurrentFolder(page, ["My workspace"]);

  await page.getByRole("button", { name: "Search" }).click();

  const input = page.getByRole("combobox", { name: "Quick search input" });
  await expect(input).toBeVisible();
  await input.fill("meetings");

  const button = page.getByRole("button", { name: "Meetings" });
  await button.click();

  await expectCurrentFolder(page, ["Dev Team", "Meetings"]);
});

test("Search file and click on it", async ({ page }) => {
  await login(page, "drive@example.com");

  await page.goto("/");
  await expectCurrentFolder(page, ["My workspace"]);
  await page.getByRole("button", { name: "Search" }).click();

  const input = page.getByRole("combobox", { name: "Quick search input" });
  await expect(input).toBeVisible();
  await input.fill("budget");

  const button = page.getByRole("button", { name: "Budget report" });
  await button.click();

  const filePreview = page.getByTestId("file-preview");
  await expect(filePreview).toBeVisible();
  await expect(filePreview.getByText("Budget report")).toBeVisible();
});
