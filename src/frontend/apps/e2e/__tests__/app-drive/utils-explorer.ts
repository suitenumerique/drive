import { expect, Page } from "@playwright/test";

export const checkExplorerBreadcrumbs = async (
  page: Page,
  expected: string[],
  hidden: string[] = []
) => {
  const breadcrumbs = page.getByTestId("explorer-breadcrumbs");
  await expect(breadcrumbs).toBeVisible();

  // Check the order of breadcrumbs
  if (expected.length >= 1) {
    const breadcrumbButtons = breadcrumbs.getByTestId("breadcrumb-button");

    // Check each breadcrumb appears in the correct order
    for (let i = 0; i < expected.length; i++) {
      const button = breadcrumbButtons.nth(i);
      await expect(button).toBeVisible();
      await expect(button).toContainText(expected[i]);
    }
  }
};
