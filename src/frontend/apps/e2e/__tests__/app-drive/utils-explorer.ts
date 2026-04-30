import { expect, Page } from "@playwright/test";
import { expectTreeItemIsSelected } from "./utils-tree";
import { PageOrLocator } from "./utils/types-utils";

export const expectExplorerBreadcrumbs = async (
  page: PageOrLocator,
  expected: string[],
  hidden: string[] = [],
) => {
  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  await expect(breadcrumbs).toBeVisible();

  // Check the order of breadcrumbs
  if (expected.length >= 1) {
    // Select the buttons but not the last one that is the share button if it exists.
    const breadcrumbButtons = breadcrumbs.locator(
      'button:not([data-testid="share-button"]), [role="button"]:not([data-testid="share-button"])',
    );

    await expect(breadcrumbButtons).toHaveCount(expected.length);

    // Check each breadcrumb appears in the correct order
    for (let i = 0; i < expected.length; i++) {
      const button = breadcrumbButtons.nth(i);
      await expect(button).toBeVisible();
      await expect(button).toContainText(expected[i]);
    }
  }
};

export const expectCurrentFolder = async (
  page: Page,
  expected: string[],
  isSelected: boolean = false,
) => {
  await expectTreeItemIsSelected(
    page,
    expected[expected.length - 1],
    isSelected,
  );
  await expectExplorerBreadcrumbs(page, expected);
};

export const expectDefaultRoute = async (
  page: Page,
  breadcrumbLabel: string,
  route: string,
) => {
  // Scope to the visible breadcrumbs container — the Breadcrumbs measurement
  // layer is a hidden sibling that renders a duplicate of every test id it
  // contains, so a page-level lookup would be ambiguous in strict mode.
  const defaultRouteButton = page
    .getByTestId("explorer-breadcrumbs")
    .getByTestId("default-route-button");
  await expect(defaultRouteButton).toBeVisible();
  await expect(defaultRouteButton).toContainText(breadcrumbLabel);
  await page.waitForURL((url) => url.toString().includes(route));
};

export const clickOnBreadcrumbButtonAction = async (
  page: Page,
  actionName: string,
) => {
  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  await expect(breadcrumbs).toBeVisible();
  const lastBreadcrumbButton = breadcrumbs
    .getByTestId("breadcrumb-button")
    .last();
  await lastBreadcrumbButton.click();
  await page.getByRole("menuitem", { name: actionName }).click();
};
