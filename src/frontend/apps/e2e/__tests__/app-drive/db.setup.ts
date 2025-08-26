import { test as setup } from "@playwright/test";

import { clearDb } from "./utils-common";

setup("clear the database", async () => {
  await clearDb();
});
