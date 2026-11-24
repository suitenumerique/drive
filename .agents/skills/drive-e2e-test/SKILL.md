---
name: drive-e2e-test
description: Work on end-to-end tests for La Suite Drive using Playwright. Use this skill when creating, modifying, debugging, or reviewing E2E tests, especially under src/frontend/apps/e2e/__tests__/app-drive. Prefer focused Chromium tests, reuse existing utilities and existing tests before creating new code, and avoid running the full E2E suite unless explicitly necessary.
---

# Drive E2E tests

The Playwright tests live in `src/frontend/apps/e2e/__tests__/app-drive`
(and `__tests__/sdk-consumer` for the picker SDK). E2E tests are the most
expensive tests of the repository: keep the suite small, run as little of it
as possible, and only on Chromium.

## Run

Most scenarios start by **truncating the database** (`clearDb()` runs
`make clear-db-e2e`); a few only reset what they use, through a fixture. So
the tests run against a dedicated database, `drive_e2e`, with its own
settings (`env.d/development/common.e2e`).

1. Once: `make bootstrap-e2e` (builds the backend image, migrates the e2e
   database, installs the frontend on the host). It does not build the mail
   templates (`src/backend/core/templates/mail/`, gitignored), which the
   scenarios that send a mail (sharing) need: when that folder is empty, run
   `make mails-install` and `make mails-build`.
2. Switch the backend to the e2e database: `make run-backend-e2e`. Check with
   `make is-e2e-backend-running`. Tell the user: their development backend is
   replaced until `make run-backend` is run again. Their development data is
   kept (`data/postgresql.local`).
3. Install only Chromium, once: `yarn install-playwright chromium`, from
   `src/frontend/apps/e2e`.
4. Run the narrowest scope, from `src/frontend/apps/e2e`:

   ```bash
   yarn test __tests__/app-drive/<file>.spec.ts --project=chromium -g "<test name>"
   ```

5. When done, put the development backend back: `make run-backend`.

- Playwright starts the frontend itself (`yarn dev` in `apps/drive`), or
  reuses whatever already answers on :3000.
- There is one worker and no parallelism, because every test shares the
  database: never start two Playwright runs at once.
- `make run-tests-e2e -- <args>` also works, but make ends with a "No rule to
  make target" error on the extra arguments: prefer `yarn test`.
- `sdk-consumer/picker.spec.ts` also needs the SDK built and its demo app on
  :5173: `make build-frontend-sdk`, then `make run-frontend-sdk-development`
  in the background.
- Never run Firefox or WebKit (`--project=firefox|webkit`) unless asked. Never
  run the whole suite (`yarn test` with no file) unless asked, or after a
  change to the shared E2E setup.
- For debugging, add `--ui` or `--headed`.

Widen only when needed: one test, then its spec file, then closely related
specs.

### Without yarn on the host

No image of the compose stack holds the E2E workspace or the browsers:
locally, Playwright runs on the host, and `make bootstrap-e2e` needs yarn
for its last step. (The CI keeps the tests on the runner and takes the
browsers from the official Playwright image, see
`.github/workflows/drive-frontend.yml`.) When `command -v yarn` fails:

- Serve the frontend with its container and wait until it answers:
  `DOCKER_USER=$(id -u):$(id -g) docker compose up -d frontend-dev`.
  Playwright reuses it instead of starting `yarn dev`.
- If Node is installed and `src/frontend/node_modules` exists, call the
  binaries with `npx --no-install` from `src/frontend/apps/e2e`:
  `npx --no-install playwright install --with-deps chromium`,
  `npx --no-install playwright test <file> --project=chromium -g "<name>"`.
- Otherwise E2E tests cannot run: say so and report them as not run. Do not
  install yarn or the dependencies without asking.

## Reuse before writing

Search the existing specs and helpers for the feature, its UI labels and a
similar workflow before writing any Playwright code. The helpers often hold
the synchronization a test needs: do not replace them with bare clicks.

| file (`__tests__/app-drive/`) | helpers |
|---|---|
| `utils-common.ts` | `clearDb`, `login` (no Keycloak: the e2e endpoint of the backend creates the user and logs it in), `keyCloakSignIn`, `runFixture`, `MultiUserTest` (two users, `userA` and `userB`) |
| `utils-item.ts` | `createFolder`, `createFolderInCurrentFolder`, `createFileFromTemplate`, `importFile`, `deleteCurrentFolder`, `getNewButton` |
| `utils-navigate.ts` | `clickToMyFiles`, `clickToRecent`, `clickToSharedWithMe`, `clickToFavorites`, `clickToTrash`, `navigateToFolder` |
| `utils-explorer.ts` | `expectExplorerBreadcrumbs`, `expectCurrentFolder`, `expectDefaultRoute` |
| `utils-embedded-grid.ts` | `getRowItem`, `expectRowItem`, `expectRowItemIsNotVisible`, `clickOnRowItemActions` |
| `utils-tree.ts` | `getItemTree`, `openTreeNode`, `clickOnItemInTree`, `expectTreeItemIsSelected` |
| `utils/share-utils.ts` | `openShareModal`, `closeShareModal`, `expectUserInMembersList`, `selectLinkReach`, `expectAllowedRoles` |
| `utils/upload-utils.ts` | `uploadFile`, `setupUploadTest`, `mockSlowUpload`, `getUploadToast` |
| `utils/move-utils.ts` | `getMoveFolderModal`, `acceptMoveItem`, `searchAndSelectItem` |
| `utils/restriction-utils.ts` | the world and helpers of the `folder-restrictions-*.spec.ts` files |
| `utils/starred-utils.ts`, `utils/custom-columns-utils.ts` | favorites, grid columns and sorting |

A scenario that needs data the UI cannot build quickly uses a **fixture**: a
management command of the backend `e2e` app
(`src/backend/e2e/management/commands/e2e_fixture_*.py`), run with
`runFixture("e2e_fixture_<name>")`. A setting the scenario depends on goes in
`env.d/development/common.e2e`, with a comment naming the spec.

When a helper almost fits, give it a sensible optional argument rather than
copying it into the test. Do not turn a helper into a catch-all with
unrelated options.

## Add as little as possible

1. Can an existing test assert the new behaviour cheaply and still read well?
   Extend it.
2. Does the behaviour need E2E at all? A backend test, or a Jest test of the
   extracted logic, is often enough. E2E is for user workflows and
   frontend/backend integration: uploading, sharing and permissions, moving,
   the trash, sign-in, the editors.
3. Otherwise, add a focused test to the existing spec of the feature. Create a
   new spec file only when no feature file fits.

Do not repeat a scenario that differs from an existing one by a single action.

## Write reliable tests

- Selectors: `getByRole`, `getByLabel`, `getByText`, then `getByTestId`. No
  generated classes, DOM paths or indexes. Do not add a `data-testid` when an
  accessible selector is stable. Match a button by its exact accessible name
  when another one contains it (`{ name: "New", exact: true }`).
- Waits: web-first assertions (`await expect(locator).toBeVisible()`),
  awaited responses or URL changes. No `waitForTimeout` to fix a race, even
  if older tests do it.
- Independence: a test sets its own starting state (`clearDb()`, or a
  fixture that resets what it uses) before `login(page, email)`, never
  depends on another one or on its order, and creates only the data it needs.
- Several users: `MultiUserTest`, and wait for the visible result of the other
  user's action, never a fixed delay.
- A flaky test is a bug: find the missing synchronization point (missing
  `await`, unawaited request, unstable selector) instead of raising a timeout.

## Before finishing

- Review `git diff`: no unrelated test changed, helpers reused, no new sleep,
  no duplicated scenario. The CI does not lint the E2E workspace, and the
  workspace holds no ESLint configuration: the review is the check.
- Report the tests reused, modified or created (and why a new one was
  needed), the exact commands run, that only Chromium was used, whether the
  development backend was put back, and what was not verified. Never claim
  the whole suite or another browser passed without running it.
