import { expect, Page } from "@playwright/test";
import { clickOnRowItemActions, getRowItem } from "./utils-embedded-grid";
import { API, findItem, itemUrl, names, test } from "./utils/restriction-utils";

const metadataUrl = "**/items/deletion-info/";
const dialog = (page: Page) => page.getByRole("dialog");

for (const source of ["row", "selection bar"]) {
  for (const dismissal of ["Cancel", "Close", "Escape"]) {
    test(`${source}: ${dismissal} preserves the selection and sends no deletion`, async ({
      page,
      folders,
    }) => {
      // 1. Select a parent containing restricted folders and remember the current
      // route so we can verify that dismissing confirmation leaves it unchanged.
      await page.goto(itemUrl("my-files"));
      await (await getRowItem(page, names.parent)).click();
      const originalUrl = page.url();

      // 2. Record DELETE requests before opening the confirmation. Dismissal
      // must never send one, regardless of the menu or dismissal method used.
      const deletes: string[] = [];
      page.on("request", (request) => {
        if (request.method() === "DELETE") deletes.push(request.url());
      });

      // 3. Request deletion from the row menu or selection bar and check that
      // the warning explains why restricted folders need special handling.
      if (source === "row")
        await clickOnRowItemActions(page, names.parent, "Delete");
      else
        await page
          .locator(".explorer__selection-bar")
          .getByRole("button", { name: "Delete", exact: true })
          .click();
      await expect(dialog(page)).toContainText("Delete this folder?");
      await expect(dialog(page).locator("strong")).toHaveText(
        "restricted folder",
      );

      // 4. Dismiss using Cancel, the close button, or Escape for this iteration.
      if (dismissal === "Escape") await page.keyboard.press("Escape");
      else
        await dialog(page)
          .getByRole("button", {
            name: dismissal === "Close" ? "close" : dismissal,
            exact: true,
          })
          .click();

      // 5. The modal closes while selection and navigation stay unchanged.
      // No DELETE was sent, and the parent remains retrievable through the API.
      await expect(dialog(page)).toHaveCount(0);
      await expect(page.locator("tr.selected")).toHaveCount(1);
      expect(page.url()).toBe(originalUrl);
      expect(deletes).toEqual([]);
      expect(
        (await page.request.get(`${API}/items/${folders.parent.id}/`)).ok(),
      ).toBeTruthy();
    });
  }
}

for (const entryPoint of ["selection bar", "keyboard"]) {
  test(`${entryPoint}: one batch request, explicit confirmation, and restricted targets survive`, async ({
    page,
    folders,
  }) => {
    // 1. Prepare a mixed selection: a parent containing restricted folders and
    // an ordinary folder. Move the ordinary folder to the root so both appear
    // side by side in My files. Keep the restricted target's ID for the final check.
    const normal = findItem(folders.items, names.normal);
    const target = findItem(folders.items, names.accessible).target!;
    const csrf = (await page.context().cookies(API)).find(
      (cookie) => cookie.name === "csrftoken",
    )!.value;
    const moved = await page.request.post(`${API}/items/${normal.id}/move/`, {
      data: {},
      headers: { "X-CSRFToken": csrf },
    });
    expect(moved.ok()).toBeTruthy();

    // 2. Select both folders, using Ctrl/Cmd-click to extend the selection.
    await page.goto(itemUrl("my-files"));
    await (await getRowItem(page, names.parent)).click();
    await (
      await getRowItem(page, names.normal)
    ).click({ modifiers: ["ControlOrMeta"] });
    await expect(page.locator("tr.selected")).toHaveCount(2);

    // 3. Record metadata checks and DELETE requests before starting deletion.
    const checks: string[][] = [];
    const deletes: string[] = [];
    page.on("request", (request) => {
      if (request.url().endsWith("/deletion-info/"))
        checks.push(request.postDataJSON().ids);
      if (request.method() === "DELETE") deletes.push(request.url());
    });

    // 4. Request deletion through the entry point covered by this test iteration.
    if (entryPoint === "keyboard")
      await page.keyboard.press("ControlOrMeta+Backspace");
    else
      await page
        .locator(".explorer__selection-bar")
        .getByRole("button", { name: "Delete", exact: true })
        .click();

    // 5. Both IDs must be checked in one request. The confirmation must appear
    // before any DELETE is sent because the parent contains restricted folders.
    await expect(dialog(page)).toContainText("Delete these items?");
    expect(checks).toHaveLength(1);
    expect(checks[0].sort()).toEqual([folders.parent.id, normal.id].sort());
    expect(deletes).toEqual([]);

    // 6. Repeating the shortcut while confirmation is open must not start
    // another metadata check.
    await page.keyboard.press("ControlOrMeta+Backspace");
    expect(checks).toHaveLength(1);

    // 7. Confirm deletion and wait for the ordinary folder's DELETE response.
    // Register the response listener before clicking so a fast response is caught.
    const deleted = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/items/${normal.id}/`) &&
        response.request().method() === "DELETE",
    );
    await dialog(page)
      .getByRole("button", { name: "Delete", exact: true })
      .click();
    expect((await deleted).ok()).toBeTruthy();

    // 8. Successful deletion clears the selection and removes the parent row,
    // without fetching deletion metadata again.
    await expect(page.locator("tr.selected")).toHaveCount(0);
    await expect(page.getByRole("row", { name: names.parent })).toHaveCount(0);
    expect(checks).toHaveLength(1);

    // 9. The restricted target survives its parent's deletion: it is not trashed
    // and its children can still be listed through the API.
    const preserved = await page.request.get(`${API}/items/${target.id}/`);
    expect(preserved.ok()).toBeTruthy();
    expect((await preserved.json()).deleted_at).toBeNull();
    expect(
      (await page.request.get(`${API}/items/${target.id}/children/`)).ok(),
    ).toBeTruthy();
  });
}

for (const failure of ["forbidden", "incomplete"]) {
  test(`metadata ${failure} blocks deletion and allows retry`, async ({
    page,
    folders,
  }) => {
    // 1. Select an ordinary folder and record DELETE requests. A failed metadata
    // check must block deletion even when no confirmation would normally be needed.
    await page.goto(itemUrl(folders.parent.id));
    await (await getRowItem(page, names.normal)).click();
    const deletes: string[] = [];
    page.on("request", (request) => {
      if (request.method() === "DELETE") deletes.push(request.url());
    });

    // 2. Simulate either a forbidden metadata request or a successful response
    // missing the selected ID. Both responses must prevent deletion.
    await page.route(metadataUrl, (route) =>
      route.fulfill({
        status: failure === "forbidden" ? 403 : 200,
        contentType: "application/json",
        body: JSON.stringify(
          failure === "forbidden" ? { detail: "Forbidden" } : {},
        ),
      }),
    );

    // 3. Request deletion and verify the error feedback. Keep the selection,
    // send no DELETE, and do not show confirmation based on invalid metadata.
    await clickOnRowItemActions(page, names.normal, "Delete");
    await expect(
      page.getByText("An error occurred while deleting the item."),
    ).toBeVisible();
    await expect(page.locator("tr.selected")).toHaveCount(1);
    expect(deletes).toEqual([]);
    await expect(dialog(page)).toHaveCount(0);

    // 4. Restore real metadata responses and listen for DELETE before retrying.
    // This ordinary folder should now delete successfully without confirmation.
    await page.unroute(metadataUrl);
    const normal = findItem(folders.items, names.normal);
    const deleted = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/items/${normal.id}/`) &&
        response.request().method() === "DELETE",
    );
    await clickOnRowItemActions(page, names.normal, "Delete");
    expect((await deleted).ok()).toBeTruthy();
    await expect(dialog(page)).toHaveCount(0);
  });
}

for (const mobile of [false, true]) {
  test(`${mobile ? "mobile" : "desktop"}: restricted breadcrumb survives direct URL and reload`, async ({
    page,
    folders,
  }) => {
    // 1. Open the accessible restricted target directly, then reload. This checks
    // that its parent hierarchy does not depend on earlier navigation history.
    if (mobile) await page.setViewportSize({ width: 375, height: 667 });
    const target = findItem(folders.items, names.accessible).target!;
    await page.goto(itemUrl(target.id));
    await page.reload();

    // 2. Both layouts must display the original parent and restricted folder,
    // even though the restricted target is stored as a separate physical root.
    const breadcrumbs = page.locator(
      mobile
        ? ".explorer__content__breadcrumbs--mobile"
        : ".explorer__content__breadcrumbs",
    );
    await expect(breadcrumbs).toContainText(names.parent);
    await expect(breadcrumbs).toContainText(names.accessible);

    // 3. Navigate back via the mobile back button or desktop parent breadcrumb.
    // Verify the actual parent route and its listing of the restricted entry.
    if (mobile)
      await breadcrumbs.getByRole("button", { name: "chevron_left" }).click();
    else await breadcrumbs.getByText(names.parent, { exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/items/${folders.parent.id}$`));
    await expect(await getRowItem(page, names.accessible)).toBeVisible();
  });
}

test("failed deletion keeps navigation and selection until a successful retry", async ({
  page,
  folders,
}) => {
  // 1. Select an ordinary folder and remember the route before deletion starts.
  await page.goto(itemUrl(folders.parent.id));
  const normal = findItem(folders.items, names.normal);
  await (await getRowItem(page, names.normal)).click();
  const url = page.url();

  // 2. Allow real metadata and read requests, but reject the actual DELETE.
  // This isolates a deletion failure from a failure during the metadata check.
  await page.route(`**/items/${normal.id}/`, (route) => {
    if (route.request().method() !== "DELETE") return route.fallback();
    return route.fulfill({
      status: 403,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Forbidden" }),
    });
  });

  // 3. Delete through the selection bar. The error must leave the user on the
  // same page with the folder still selected, rather than redirecting or hiding it.
  await page
    .locator(".explorer__selection-bar")
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  await expect(
    page.getByText("An error occurred while deleting the item."),
  ).toBeVisible();
  expect(page.url()).toBe(url);
  await expect(page.locator("tr.selected")).toHaveCount(1);

  // 4. Remove the rejection and retry with the existing selection. Only a
  // successful deletion should remove the row and dismiss the selection bar.
  await page.unroute(`**/items/${normal.id}/`);
  await page
    .locator(".explorer__selection-bar")
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  await expect(page.getByRole("row", { name: names.normal })).toHaveCount(0);
  await expect(page.locator(".explorer__selection-bar")).toHaveCount(0);
});

test("repeated shortcuts cannot submit again during metadata checks or deletion", async ({
  page,
  folders,
}) => {
  // 1. Select an ordinary folder so the flow goes from metadata to deletion
  // without a confirmation modal between the two requests.
  await page.goto(itemUrl(folders.parent.id));
  const normal = findItem(folders.items, names.normal);
  await (await getRowItem(page, names.normal)).click();

  // 2. Create separate gates for metadata and DELETE. Each promise holds its
  // request until explicitly released, allowing checks during both pending states
  // without relying on arbitrary delays.
  let releaseMetadata!: () => void;
  const metadataGate = new Promise<void>((resolve) => {
    releaseMetadata = resolve;
  });
  let releaseDelete!: () => void;
  const deleteGate = new Promise<void>((resolve) => {
    releaseDelete = resolve;
  });

  // 3. Record each request, pause it at its gate, then let it reach the real API.
  // Other requests, such as reads of the selected item, continue normally.
  const checks: string[][] = [];
  const deletes: string[] = [];
  await page.route(metadataUrl, async (route) => {
    checks.push(route.request().postDataJSON().ids);
    await metadataGate;
    await route.continue();
  });
  await page.route(`**/items/${normal.id}/`, async (route) => {
    if (route.request().method() !== "DELETE") return route.fallback();
    deletes.push(route.request().url());
    await deleteGate;
    await route.continue();
  });

  // 4. Start deletion and repeat the shortcut while metadata is still pending.
  // The Delete button must be disabled during this first waiting period.
  await page.keyboard.press("ControlOrMeta+Backspace");
  await expect.poll(() => checks.length).toBe(1);
  const button = page
    .locator(".explorer__selection-bar")
    .getByRole("button", { name: "Delete", exact: true });
  await expect(button).toBeDisabled();
  await page.keyboard.press("ControlOrMeta+Backspace");

  // 5. Release metadata, but keep DELETE pending. Selection must remain visible
  // and repeating the shortcut must still be blocked during the actual deletion.
  releaseMetadata();
  await expect.poll(() => deletes.length).toBe(1);
  await expect(page.locator("tr.selected")).toHaveCount(1);
  await page.keyboard.press("ControlOrMeta+Backspace");
  await expect(button).toBeDisabled();

  // 6. Let deletion finish. Despite the repeated shortcuts, the entire attempt
  // must have sent exactly one metadata request and one DELETE.
  releaseDelete();
  await expect(page.locator(".explorer__selection-bar")).toHaveCount(0);
  expect(checks).toEqual([[normal.id]]);
  expect(deletes).toHaveLength(1);
});
