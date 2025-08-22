import { expect, Page } from "@playwright/test";

export const keyCloakSignIn = async (
  page: Page,
  username: string,
  password: string,
  fromHome: boolean = true
) => {
  if (fromHome) {
    await page
      .getByRole("button", { name: "Participate to the alpha" })
      .first()
      .click();
  }

  await expect(page.getByText("Sign in to your account").first()).toBeVisible();

  if (await page.getByLabel("Restart login").isVisible()) {
    await page.getByLabel("Restart login").click();
  }

  await page.getByRole("textbox", { name: "username" }).fill(username);
  await page.getByRole("textbox", { name: "password" }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).first().click();
};

export const getStorageState = (username: string) => {
  return `${__dirname}/../../playwright/.auth/user-${username}.json`;
};
