import { expect, Page } from "@playwright/test";
import { exec } from "child_process";
import path from "path";
// We need to use __dirname to get the root path of the project
// because Playwright runs tests in a different directory from the root
// by default.
const ROOT_PATH = path.join(__dirname, "/../../../../../..");
const CLEAR_DB_TARGET = "clear-db-e2e";

/**
 * Sign in through the development OIDC provider (Dex, see docker/auth/dex.yaml).
 * Dex authenticates users by email address.
 */
export const oidcSignIn = async (
  page: Page,
  email: string,
  password: string,
  fromHome: boolean = true,
) => {
  if (fromHome) {
    await page.getByRole("button", { name: "Sign in" }).first().click();
  }

  await expect(
    page.getByRole("heading", { name: "Log in to Your Account" }),
  ).toBeVisible();

  await page.getByRole("textbox", { name: "Email Address" }).fill(email);
  await page.getByRole("textbox", { name: "Password" }).fill(password);
  await page.getByRole("button", { name: "Login" }).click();
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
      `cd ${ROOT_PATH} && LC_ALL=C make ${target}`,
      (error: Error | null, stdout: string, stderr: string) => {
        if (error) {
          // Ignore "No rule to make target" errors (the pseudo-target hack of
          // backend-exec-command; make may prefix it with "make[N]:"). LC_ALL=C
          // keeps the message in English regardless of the machine locale.
          if (error.message.includes("No rule to make target")) {
            resolve(stdout);
            return;
          }
          console.error(`Error executing command: ${error}`);
          reject(error);
          return;
        }
        resolve(stdout);
      },
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
