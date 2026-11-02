import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { createFolder } from "./utils-item";
import { getRowItem } from "./utils-embedded-grid";

const LONG_TITLE =
  "A very long folder name that cannot fit in the name column of the " +
  "explorer grid and therefore gets truncated with an ellipsis at the end";
const SHORT_TITLE = "Short";

test("Shows the full title in a tooltip only when it is truncated", async ({
  page,
}) => {
  // 1. Start from an empty drive with one folder whose title overflows the
  // name column, and one whose title fits.
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await createFolder(page, LONG_TITLE);
  await getRowItem(page, LONG_TITLE);
  await createFolder(page, SHORT_TITLE);
  await getRowItem(page, SHORT_TITLE);

  // The mobile cell reuses the same class but is hidden on desktop, so only
  // keep the visible title.
  const tooltip = page.locator(".c__tooltip__content");
  const titleText = (title: string) =>
    page
      .locator(".explorer__grid__item__name__text")
      .filter({ hasText: title, visible: true });
  const longTitleText = titleText(LONG_TITLE);
  const shortTitleText = titleText(SHORT_TITLE);

  // 2. Sanity check: the long title is visually truncated, otherwise the
  // tooltip is legitimately not rendered and the test would prove nothing.
  await expect
    .poll(() => longTitleText.evaluate((el) => el.scrollWidth > el.clientWidth))
    .toBe(true);

  // 3. Hovering the truncated title opens a tooltip with the full title.
  await longTitleText.hover();
  await expect(tooltip).toBeVisible();
  await expect(tooltip).toHaveText(LONG_TITLE);

  // 4. Moving away closes it.
  await page.mouse.move(0, 0);
  await expect(tooltip).not.toBeVisible();

  // 5. A title that fits does not get a tooltip.
  await shortTitleText.hover();
  await expect(tooltip).not.toBeVisible();
});
