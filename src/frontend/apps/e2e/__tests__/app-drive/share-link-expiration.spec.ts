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
  await expect(picker).toBeVisible();
  await picker.getByRole("button", { name: "Next month" }).click();
  await picker
    .getByRole("button", { name: new RegExp(customDate.calendarLabel) })
    .click();
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
