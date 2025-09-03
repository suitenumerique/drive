import { expect, Page } from "@playwright/test";
import { exec } from "child_process";
import path from "path";
// We need to use __dirname to get the root path of the project
// because Playwright runs tests in a different directory from the root
// by default.
const ROOT_PATH = path.join(__dirname, "/../../../../../..");
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
  await runTarget(CLEAR_DB_TARGET);
};

export const runFixture = async (fixture: string) => {
  await runTarget(`backend-exec-command ${fixture}`);
};

export const runTarget = async (target: string) => {
  await new Promise((resolve, reject) => {
    exec(
      `cd ${ROOT_PATH} && make ${target}`,
      (error: Error | null, stdout: string, stderr: string) => {
        if (error) {
          // Ignore "No rule to make target" errors
          if (error.message.includes("make: *** No rule to make target")) {
            resolve(stdout);
            return;
          }
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
