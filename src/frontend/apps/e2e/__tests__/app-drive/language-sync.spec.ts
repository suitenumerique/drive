import test, { expect } from "@playwright/test";

import { clearDb, login } from "./utils-common";

const API_BASE = "http://localhost:8071/api/v1.0";

test("Backend user language syncs to browser on load", async ({ page }) => {
  await clearDb();
  await login(page, "user-lang@example.com");

  // Navigate first to get the CSRF cookie set by Django
  await page.goto("/");
  await expect(page.getByText("Drop your files here")).toBeVisible({
    timeout: 10000,
  });

  // Extract the CSRF token from cookies
  const cookies = await page.context().cookies();
  const csrfToken =
    cookies.find((c) => c.name === "csrftoken")?.value ?? "";

  // Fetch the user id
  const meResponse = await page.request.get(`${API_BASE}/users/me/`);
  const me = await meResponse.json();

  // Set the user's language to French via the API
  const patchResponse = await page.request.patch(`${API_BASE}/users/${me.id}/`, {
    headers: { "X-CSRFToken": csrfToken },
    data: { language: "fr-fr" },
  });
  expect(patchResponse.status()).toBe(200);

  // Reload so the hook picks up the new language
  await page.goto("/");

  // The app should sync the backend language to the browser
  await expect(page.getByText("Déposez vos fichiers ici")).toBeVisible({
    timeout: 10000,
  });

  const htmlLang = await page.evaluate(() =>
    document.documentElement.getAttribute("lang")
  );
  expect(htmlLang).toBe("fr-FR");
});

test("Browser language syncs to backend for new user", async ({ page }) => {
  await clearDb();
  await login(page, "new-user-lang@example.com");

  // Before navigating, the freshly created user should have no language
  const meBefore = await page.request.get(`${API_BASE}/users/me/`);
  const userBefore = await meBefore.json();
  expect(userBefore.language).toBeNull();

  await page.goto("/");

  // Wait for the app to fully load
  await expect(page.getByText("Drop your files here")).toBeVisible({
    timeout: 10000,
  });

  // The hook should have synced the browser locale (en-US → en-us) to the backend
  const meAfter = await page.request.get(`${API_BASE}/users/me/`);
  const userAfter = await meAfter.json();
  expect(userAfter.language).toBe("en-us");
});
