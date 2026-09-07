import path from "path";

import test, { expect, Page } from "@playwright/test";

import { clearDb, login } from "./utils-common";

const API_BASE = "http://localhost:8071/api/v1.0";

const DOCX_FILE_PATH = path.join(__dirname, "/assets/empty_doc.docx");

/**
 * Flags every file as editable online, so the test reaches the WOPI
 * intermediate page without depending on the Collabora discovery.
 */
const mockWopiSupported = async (page: Page) => {
  await page.route(
    (url) => /\/api\/v1\.0\/items(\/|$)/.test(url.pathname),
    async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      const response = await route.fetch();
      const json = await response.json();
      const markSupported = (item: Record<string, unknown>) => {
        if (item?.type === "file") {
          item.is_wopi_supported = true;
        }
      };
      if (Array.isArray(json?.results)) {
        json.results.forEach(markSupported);
      } else if (json?.id) {
        markSupported(json);
      }
      await route.fulfill({ response, json });
    }
  );
};

test("Backend user language syncs to browser on load", async ({ page }) => {
  await clearDb();
  await login(page, "user-lang@example.com");

  // Navigate first to get the CSRF cookie set by Django
  await page.goto("/");
  await expect(page.getByText("This tab is empty")).toBeVisible({
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
  await expect(page.getByText("Cet onglet est vide")).toBeVisible({
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
  await expect(page.getByText("This tab is empty")).toBeVisible({
    timeout: 10000,
  });

  // The hook should have synced the browser locale (en-US → en-us) to the backend
  const meAfter = await page.request.get(`${API_BASE}/users/me/`);
  const userAfter = await meAfter.json();
  expect(userAfter.language).toBe("en-us");
});

test.describe("browser language without a region", () => {
  // Firefox in French announces "fr" where Chrome announces "fr-FR". Both must
  // end up on the French we ship.
  test.use({ locale: "fr" });

  test("Region-less browser language reaches the design system", async ({
    page,
  }) => {
    await clearDb();
    await login(page, "regionless-lang@example.com");
    await mockWopiSupported(page);

    await page.goto("/");
    await expect(page.getByText("Cet onglet est vide")).toBeVisible({
      timeout: 10000,
    });

    // "fr" is widened to "fr-fr", not left as-is nor fallen back to English
    const htmlLang = await page.evaluate(() =>
      document.documentElement.getAttribute("lang")
    );
    expect(htmlLang).toBe("fr-FR");

    // and it reaches the backend, so the WOPI editor opens in French too
    await expect
      .poll(
        async () => {
          const me = await page.request.get(`${API_BASE}/users/me/`);
          return (await me.json()).language;
        },
        { timeout: 10000 }
      )
      .toBe("fr-fr");

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Importer" }).click();
    await page.getByRole("menuitem", { name: "Importer des fichiers" }).click();
    await (await fileChooserPromise).setFiles(DOCX_FILE_PATH);
    await expect(
      page.getByRole("cell", { name: "empty_doc", exact: true })
    ).toBeVisible({ timeout: 10000 });

    // The intermediate page is what a public share link opens on an office
    // file. Its labels come from the design system, which only ships "fr-FR":
    // a region-less language used to silently fall back to English there.
    const itemsResponse = await page.request.get(`${API_BASE}/items/?type=file`);
    const items = await itemsResponse.json();
    const item = (items.results ?? items).find(
      (candidate: { title: string }) => candidate.title.startsWith("empty_doc")
    );
    await page.goto(`/explorer/items/files/${item.id}`);

    await expect(
      page.getByText(
        "Ce fichier peut être modifié avec un éditeur en ligne. Il s'ouvre dans un nouvel onglet."
      )
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: "Ouvrir dans l'éditeur" })
    ).toBeVisible();
    await expect(page.getByText("Open in editor")).toBeHidden();
  });
});
