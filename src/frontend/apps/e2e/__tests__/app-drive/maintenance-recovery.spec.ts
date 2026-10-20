/**
 * There is no complete end-to-end test of a batch recovery, on purpose: the
 * maintenance tool belongs to the encryption service, which Drive does not depend
 * on. This test runs the real tool only when MAINTENANCE_TOOL names it (a path to
 * the built file, or the URL a deployed encryption service serves it at,
 * /public-assets/maintenance-tool.html), and is skipped otherwise. Running it by
 * hand (before a release, before a real recovery) is a first step. To run it
 * regularly, there are two ways, each with its cost: CI fetches the tool from a
 * production instance (it always tests what a recovery would really use, but CI
 * then depends on that instance being reachable); or a copy of the file is
 * committed here (CI is self-contained, but the copy drifts from the deployed tool
 * until someone updates it). The fixtures under
 * src/backend/core/tests/maintenance_fixture (made once with the encryption
 * service's code for its development phrase) are tested on every run without a
 * browser: they cover the export and import formats, not the tool.
 *
 *   MAINTENANCE_TOOL=<encryption checkout>/dist/maintenance/maintenance-tool.html \
 *     yarn test --project chromium maintenance-recovery
 *
 * Flows: the fixture's trees seeded for the e2e user, exported for the development
 * key in the backend container, decrypted in the tool, the archive imported, then
 * the tree opened in Drive in plaintext; and the same recovery after the copies
 * were rotated to a second development key through the tool's Rotate tab.
 */
import { execFile } from "child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync } from "fs";
import os from "os";
import path from "path";
import { pathToFileURL } from "url";
import { promisify } from "util";

import test, { Browser, Page, expect } from "@playwright/test";

import { login } from "./utils-common";

const ROOT_PATH = path.join(__dirname, "/../../../../../..");
const FIXTURE = JSON.parse(
  readFileSync(
    path.join(
      ROOT_PATH,
      "src/backend/core/tests/maintenance_fixture/drive-trees.json",
    ),
    "utf8",
  ),
);
const TOOL = process.env.MAINTENANCE_TOOL;
const USER = "drive@example.com";
const ROOT_ID: string = FIXTURE.maintenance.roots[0];
const OTHER_ROOT_ID: string = FIXTURE.otherOrganization.roots[0];
// Inside the backend container: what the export writes and the import reads.
const WORKDIR = "/tmp/maintenance-recovery-e2e";

const run = promisify(execFile);

const compose = async (...args: string[]) =>
  (await run("docker", ["compose", ...args], { cwd: ROOT_PATH })).stdout;

const manage = (...args: string[]) =>
  compose("exec", "-T", "app-dev", "python", "manage.py", ...args);

const shell = (code: string) => manage("shell", "-c", code);

// What the code prints last: the shell may print a banner first.
const isEncrypted = async (itemId: string) =>
  (
    await shell(
      `from core.models import Item; print(Item.objects.get(pk=${JSON.stringify(itemId)}).is_encrypted)`,
    )
  )
    .trim()
    .split("\n")
    .pop();

test.describe("Batch recovery with the maintenance tool", () => {
  // One after the other: both seed the same fixed ids and use the same folder.
  test.describe.configure({ mode: "serial" });
  test.skip(!TOOL, "MAINTENANCE_TOOL names no maintenance tool");
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "Chromium only: the tool itself is tested in every browser by the encryption service",
  );

  let hostDir: string;

  test.beforeEach(async () => {
    hostDir = mkdtempSync(path.join(os.tmpdir(), "drive-maintenance-"));
    await compose("exec", "-T", "app-dev", "rm", "-rf", WORKDIR);
  });

  test.afterEach(async () => {
    rmSync(hostDir, { recursive: true, force: true });
    await compose("exec", "-T", "app-dev", "rm", "-rf", WORKDIR);
    await shell("from core.tests.maintenance_fixture import remove; remove()");
  });

  /** The tool in a context of its own, in English whatever the machine's locale. */
  const openTool = async (browser: Browser) => {
    const context = await browser.newContext({
      locale: "en-US",
      acceptDownloads: true,
    });
    const tool = await context.newPage();
    await tool.goto(/^https?:/.test(TOOL!) ? TOOL! : pathToFileURL(TOOL!).href);
    return tool;
  };

  /** An export of the container's `WORKDIR/<name>` copied out, for the tool. */
  const exportFor = async (name: string, ...args: string[]) => {
    const output = await manage(
      "maintenance_export",
      "--output",
      `${WORKDIR}/${name}`,
      ...args,
    );
    await compose("cp", `app-dev:${WORKDIR}/${name}`, hostDir);
    return output;
  };

  /** The export decrypted in the tool with `phrase`, its archive unzipped in the container and imported. */
  const recover = async (browser: Browser, name: string, phrase: string) => {
    const tool = await openTool(browser);
    await tool.setInputFiles(
      '#mt-tabpanel-decrypt input[type="file"]',
      path.join(hostDir, name),
    );
    await expect(tool.getByRole("status").first()).toHaveText(
      `${name}: 4 items, 2 files`,
    );
    await tool.locator("#mt-decrypt-word-0").fill(phrase);
    await tool
      .getByRole("button", { name: "Decrypt into a .zip archive" })
      .click();
    await expect(tool.getByText("4 items decrypted, 0 failed.")).toBeVisible();

    const [download] = await Promise.all([
      tool.waitForEvent("download"),
      tool
        .getByRole("link", { name: "Download the decrypted copy (.zip)" })
        .click(),
    ]);
    const archive = path.join(hostDir, `${name}.zip`);
    await download.saveAs(archive);
    await tool.context().close();

    await compose("cp", archive, `app-dev:${WORKDIR}/${name}.zip`);
    await compose(
      "exec",
      "-T",
      "app-dev",
      "python",
      "-m",
      "zipfile",
      "-e",
      `${WORKDIR}/${name}.zip`,
      `${WORKDIR}/${name}-decrypted`,
    );
    expect(
      await manage("maintenance_import", `${WORKDIR}/${name}-decrypted`),
    ).toContain("Switched 1 tree(s) to plaintext.");
  };

  /** In Drive, as any plaintext tree: the PDF's text, the image below; the other organization's file still sealed. */
  const expectRecovered = async (page: Page) => {
    await page.goto(`/explorer/items/${ROOT_ID}`);
    await expect(
      page.getByRole("cell", { name: "Annexes", exact: true }),
    ).toBeVisible({ timeout: 30_000 });
    await page
      .getByRole("cell", { name: "compte-rendu", exact: true })
      .dblclick();
    await expect(page.locator(".pdf-preview")).toBeVisible({ timeout: 10_000 });
    await expect(
      page.locator(".textLayer").getByText(FIXTURE.minutesText).first(),
    ).toBeAttached({ timeout: 10_000 });
    await page.keyboard.press("Escape");

    await page.getByRole("cell", { name: "Annexes", exact: true }).dblclick();
    await page.getByRole("cell", { name: "facture", exact: true }).dblclick();
    await expect(
      page.locator(".image-viewer img.image-viewer__image"),
    ).toHaveJSProperty("naturalWidth", 96, { timeout: 10_000 });

    expect(await isEncrypted(OTHER_ROOT_ID)).toBe("True");
  };

  test("an encrypted tree comes back in plaintext", async ({
    page,
    browser,
  }) => {
    test.setTimeout(180_000);

    await login(page, USER);
    await shell(
      `from core.tests.maintenance_fixture import seed; seed(${JSON.stringify(USER)})`,
    );
    expect(
      await exportFor(
        "export",
        "--fingerprint",
        FIXTURE.maintenance.fingerprint,
      ),
    ).toContain("Exported 1 tree(s): 4 item(s), 2 file(s).");

    await recover(browser, "export", FIXTURE.maintenance.phrase);
    await expectRecovered(page);
  });

  test("a tree rotated to a new maintenance key comes back with the new phrase", async ({
    page,
    browser,
  }) => {
    test.setTimeout(240_000);

    await login(page, USER);
    await shell(
      `from core.tests.maintenance_fixture import seed; seed(${JSON.stringify(USER)})`,
    );
    expect(
      await exportFor(
        "keys",
        "--keys-only",
        "--fingerprint",
        FIXTURE.maintenance.fingerprint,
      ),
    ).toContain("Exported the copies of 1 encryption root(s).");

    // The custodians re-wrap the copies: the old phrase, the new public key.
    const tool = await openTool(browser);
    await tool.getByRole("tab", { name: "Rotate the maintenance key" }).click();
    await tool.setInputFiles(
      '#mt-tabpanel-rotate input[type="file"]',
      path.join(hostDir, "keys"),
    );
    await expect(tool.getByText("keys: 1 copies")).toBeVisible();
    await tool.locator("#mt-rotate-word-0").fill(FIXTURE.maintenance.phrase);
    await tool
      .getByRole("textbox", { name: "3. The new public key" })
      .fill(FIXTURE.nextMaintenance.publicKey);
    await tool
      .getByRole("button", { name: "Rotate and download manifest.ndjson" })
      .click();
    await expect(tool.getByText("1 copies rotated, 0 failed.")).toBeVisible();

    const [download] = await Promise.all([
      tool.waitForEvent("download"),
      tool
        .getByRole("link", {
          name: "Download the rotated copies (manifest.ndjson)",
        })
        .click(),
    ]);
    mkdirSync(path.join(hostDir, "rotated"));
    await download.saveAs(path.join(hostDir, "rotated", "manifest.ndjson"));
    await tool.context().close();

    await compose("cp", path.join(hostDir, "rotated"), `app-dev:${WORKDIR}/`);
    const rotated = await manage("maintenance_rotate", `${WORKDIR}/rotated`);
    expect(rotated).toContain("Rotated the copies of 1 encryption root(s).");
    expect(rotated).not.toContain("Not rotated");

    // Nothing left for the old key: its phrase may now be destroyed.
    expect(
      await exportFor(
        "keys-after",
        "--keys-only",
        "--fingerprint",
        FIXTURE.maintenance.fingerprint,
      ),
    ).toContain("Exported the copies of 0 encryption root(s).");
    expect(
      await exportFor(
        "export",
        "--fingerprint",
        FIXTURE.nextMaintenance.fingerprint,
      ),
    ).toContain("Exported 1 tree(s): 4 item(s), 2 file(s).");

    await recover(browser, "export", FIXTURE.nextMaintenance.phrase);
    await expectRecovered(page);
  });
});
