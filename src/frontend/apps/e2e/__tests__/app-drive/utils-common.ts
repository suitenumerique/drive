import { expect, Page } from "@playwright/test";
import { exec } from "child_process";

const ROOT_PATH = "../../../..";
const CLEAR_DB_TARGET = "clear-db-e2e";

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

export const clearDb = async () => {
  await new Promise((resolve, reject) => {
    exec(
      `cd ${ROOT_PATH} && make ${CLEAR_DB_TARGET}`,
      (error: Error | null, stdout: string, stderr: string) => {
        if (error) {
          console.error(`Error executing command: ${error}`);
          reject(error);
          return;
        }
        resolve(stdout);
      }
    );
  });
};

export const login = async (page: Page, email: string) => {
  await page.request.post("http://localhost:8071/api/v1.0/e2e/user-auth/", {
    data: {
      email,
    },
  });
};

export const getStorageState = (username: string) => {
  return `${__dirname}/../../playwright/.auth/user-${username}.json`;
};
