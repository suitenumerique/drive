import { test as setup } from "@playwright/test";
import { exec } from "child_process";

const CLEAR_DB_TARGET = "clear-db-e2e";
const ROOT_PATH = "../../../..";

setup("clear the database", async () => {
  await new Promise((resolve, reject) => {
    exec(
      `cd ${ROOT_PATH} && make ${CLEAR_DB_TARGET}`,
      (error: Error | null, stdout: string, stderr: string) => {
        if (error) {
          console.error(`Error executing command: ${error}`);
          reject(error);
          return;
        }
        console.log(stdout);
        resolve(stdout);
      }
    );
  });
});
