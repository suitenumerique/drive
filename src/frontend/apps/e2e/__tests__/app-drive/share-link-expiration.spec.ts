import { expect, Page, test } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles, navigateToFolder } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import {
  closeShareModal,
  openShareModal,
  selectLinkReach,
} from "./utils/share-utils";

// Expirations are computed in the browser: its time zone (Europe/Paris) can
// differ from the one of the test runner, and a link expires at the end of the
// day in the user's time zone.
const getEndOfDay = (page: Page, date: { days?: number; monthDay?: number }) =>
  page.evaluate(({ days, monthDay }) => {
    const value = new Date();
    if (monthDay !== undefined) {
      value.setDate(1);
      value.setMonth(value.getMonth() + 1);
      value.setDate(monthDay);
    } else {
      value.setDate(value.getDate() + (days ?? 0));
    }
    value.setHours(23, 59, 59, 0);
    return {
      iso: value.toISOString(),
      label: new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(
        value,
      ),
      calendarLabel: `${value.toLocaleString("en-US", { month: "long" })} ${monthDay}, ${value.getFullYear()}`,
    };
  }, date);

const roleButton = (page: Page) =>
  page.getByTestId("share-link-role-dropdown-button");

const openLinkExpiresMenu = async (page: Page) => {
  await roleButton(page).click();
  await page.getByRole("menuitem", { name: "Link expires" }).click();
};

// Resolves with the JSON body of the next link configuration update.
const waitForLinkConfiguration = (page: Page) =>
  page
    .waitForRequest(
      (request) =>
        request.url().includes("/link-configuration/") &&
        request.method() === "PUT",
    )
    .then((request) => request.postDataJSON());

test("Set, change and remove the expiration of a share link", async ({
  page,
}) => {
  // 1. Create a folder and make its link reachable by connected users, the
  // link role dropdown holding the expiration only shows for open links.
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "Folder");
  await navigateToFolder(page, "Folder", ["My files", "Folder"]);
  await openShareModal(page);
  await selectLinkReach(page, "Connected");
  await expect(roleButton(page)).toHaveText("Reader");

  // 2. Pick the "7 days" preset: the end of that day is sent to the backend
  // and displayed next to the link role.
  const inSevenDays = await getEndOfDay(page, { days: 7 });
  await openLinkExpiresMenu(page);
  const presetBody = waitForLinkConfiguration(page);
  await page.getByRole("menuitem", { name: "7 days" }).click();
  expect(await presetBody).toMatchObject({
    link_reach: "authenticated",
    link_role: "reader",
    link_expires_at: inSevenDays.iso,
  });
  await expect(roleButton(page)).toHaveText(
    `Reader until ${inSevenDays.label}`,
  );

  // 3. Reopen the modal: the expiration comes back from the backend.
  await closeShareModal(page);
  await openShareModal(page);
  await expect(roleButton(page)).toHaveText(
    `Reader until ${inSevenDays.label}`,
  );

  // 4. Choose a custom date in the calendar, the 15th of next month.
  const customDate = await getEndOfDay(page, { monthDay: 15 });
  await openLinkExpiresMenu(page);
  await page.getByRole("menuitem", { name: "Choose date" }).click();
  const picker = page.getByTestId("share-link-expiration-picker");
  await expect(picker.getByRole("grid")).toBeVisible();
  // The calendar opens on the month of the current expiration, which can
  // already be next month: only move forward until the target day shows.
  const targetDay = picker.getByRole("button", {
    name: new RegExp(customDate.calendarLabel),
  });
  for (let clicks = 0; clicks < 2 && !(await targetDay.isVisible()); clicks++) {
    await picker.getByRole("button", { name: "Next month" }).click();
  }
  await targetDay.click();
  const customBody = waitForLinkConfiguration(page);
  await picker.getByRole("button", { name: "OK" }).click();
  expect(await customBody).toMatchObject({
    link_expires_at: customDate.iso,
  });
  await expect(picker).not.toBeVisible();
  await expect(roleButton(page)).toHaveText(`Reader until ${customDate.label}`);

  // 5. "Never" removes the expiration.
  await openLinkExpiresMenu(page);
  const neverBody = waitForLinkConfiguration(page);
  await page.getByRole("menuitem", { name: "Never" }).click();
  expect(await neverBody).toMatchObject({ link_expires_at: null });
  await expect(roleButton(page)).toHaveText("Reader");
});

test("Reopening an expired share link drops its past expiration", async ({
  page,
}) => {
  // 1. Create a folder whose link is open to connected users until a future
  // date: the backend refuses past dates, so the expiration is faked below.
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "Folder");
  await navigateToFolder(page, "Folder", ["My files", "Folder"]);
  const itemId = page.url().split("/").filter(Boolean).pop();
  await openShareModal(page);
  await selectLinkReach(page, "Connected");
  await openLinkExpiresMenu(page);
  const presetBody = waitForLinkConfiguration(page);
  await page.getByRole("menuitem", { name: "7 days" }).click();
  await presetBody;
  await closeShareModal(page);

  // 2. Serve the item as the backend does once its link has expired: the
  // stored reach and date are kept, the computed reach becomes restricted.
  const itemUrl = new RegExp(`/api/v1\\.0/items/${itemId}/(\\?.*)?$`);
  await page.route(itemUrl, async (route) => {
    const response = await route.fetch();
    const item = await response.json();
    await route.fulfill({
      response,
      json: {
        ...item,
        link_expires_at: "2020-01-01T00:00:00Z",
        computed_link_reach: "restricted",
        computed_link_role: null,
      },
    });
  });
  await openShareModal(page);
  await expect(
    page.getByTestId("share-link-reach-dropdown-button"),
  ).toContainText("Private");
  await expect(roleButton(page)).toHaveCount(0);

  // 3. Reopening the link must also clear the past date, otherwise the backend
  // keeps it and the link stays expired. The real item is served again so the
  // modal reflects what the backend stored.
  await page.unroute(itemUrl);
  const reopenBody = waitForLinkConfiguration(page);
  await selectLinkReach(page, "Connected");
  expect(await reopenBody).toMatchObject({
    link_reach: "authenticated",
    link_role: "reader",
    link_expires_at: null,
  });
  await expect(roleButton(page)).toHaveText("Reader");
});
