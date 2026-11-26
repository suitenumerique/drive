---
name: drive-frontend
description: Work safely and efficiently on the Next.js frontend of La Suite Drive (src/frontend/apps/drive). Use this skill when modifying React components, hooks, the Driver API layer, TanStack Query, the explorer, uploads, the file preview, i18n strings, styles, or Jest tests of the frontend.
---

# Drive frontend

The app lives in `src/frontend/apps/drive` (a Yarn workspace of
`src/frontend`): Next.js with the **pages router** (`src/pages/`), exported
statically, React, TanStack Query and the La Suite design system
(`@gouvfr-lasuite/ui-components`, built on Cunningham).
Read the versions in `package.json`: they move faster than any document.
The `@/` alias points to `src/`.

## Commands

From `src/frontend/apps/drive`:

| task | command |
|---|---|
| one test file | `yarn jest <path>` |
| tests importing a file | `yarn jest --findRelatedTests <path>` |
| lint the files you touched | `yarn eslint <files>` |
| type check | `yarn tsc --noEmit` |
| everything, once at the end | `yarn lint`, `yarn tsc --noEmit`, `yarn test` |

`yarn dev` serves the app on :3000 against the backend on :8071 (see the
`drive-start` skill). `yarn build` type checks but does not lint. There is no
Prettier or Stylelint configuration: keep the style of the file you edit.

### Without yarn on the host

When `command -v yarn` fails, run the same commands from the repository root
in the frontend image: its working directory is `apps/drive`, so the paths do
not change.

```bash
docker compose exec frontend-dev yarn jest <path>   # container running
DOCKER_USER=$(id -u):$(id -g) docker compose run --rm frontend-dev \
  sh -c 'yarn jest <path> && yarn eslint <files> && yarn tsc --noEmit'
```

- Pass `DOCKER_USER` as the Makefile does, so written files stay yours.
- `node_modules` is bind-mounted from `src/frontend/`: after a `package.json`
  or `yarn.lock` change, `yarn install --frozen-lockfile` in the container is
  enough. `make build-frontend` does it too, after rebuilding the image.
- `make frontend-lint` and `make run-frontend-development` call yarn on the
  host. Serve the frontend with its container instead: `make run`, or
  `DOCKER_USER=$(id -u):$(id -g) docker compose up -d frontend-dev` when the
  backend already runs.

## Where things are

- `src/features/<feature>/` holds one feature. The explorer (grid, tree,
  filters, modals, right panel, trash, uploads) is `src/features/explorer/`:
  `components/`, `hooks/` (`useQueries.tsx`, `useMutations.tsx`, one hook per
  query or mutation), `stores/`, `utils/`.
- `src/features/drivers/`: the `Driver` interface, its implementations and
  `types.ts`, the types of the API objects (`Item`, `Access`, `User`…).
- `src/features/api/`: `fetchAPI` (base URL, CSRF token, credentials, redirect
  to `/401` and `/403`), `APIError`, `errorCauses`.
- `src/features/ui/components/`: shared components (`toaster/`,
  `breadcrumbs/`, `infinite-scroll/`…). Reuse them before adding a new one.
- `src/features/layouts/`, `auth/`, `config/` (the `/config/` endpoint of the
  backend), `sdk/` (the picker embedded by other applications, pages under
  `src/pages/sdk/`), `wopi/` (the editor page).
- `src/features/i18n/translations.json`: every translation, per language.

## Conventions

- **Code quality**: DRY, KISS, and the Drive code standard (`AGENTS.md`, and
  the code around yours). Reuse an existing component, hook or helper before
  writing a new one, and add an abstraction only for a second real use.
- **API calls** go through the driver: add the method to `Driver.ts`,
  implement it in `StandardDriver.ts` on `fetchAPI`, and call it with
  `getDriver()` from a TanStack Query hook. A mutation invalidates or updates
  the keys it affects (`["items", …]`, `["itemAccesses", itemId]`…): look at
  the neighbouring hooks of `useMutations.tsx` for the keys in use.
- **Types** of API objects are named after the backend serializer.
- **Rights**: show or enable an action from the `abilities` the backend
  returns with the item (`item.abilities.update`…), never from a role computed
  on the client. The backend enforces them anyway.
- **Explorer state**: `GlobalExplorerContext` for what the explorer shares,
  and the selection store (`stores/selectionStore.ts`) for the selection. Read
  `docs/architecture/explorer-selection-store.md` before touching the
  selection or the rendering of the grid rows: it explains why the selection
  is not in a context.
- **i18n**: every user-visible string and `aria-label` goes through
  `const { t } = useTranslation()` with a **key**
  (`t("explorer.actions.restore.toast")`). Add the key by hand to **every**
  language of `translations.json`, at the same place in each: a Jest test
  fails on a missing key or an empty value.
- **Styles**: an SCSS file next to the component, and the Cunningham tokens
  rather than hard-coded colours or sizes.
- **Toasts**: `addToast` and `ToasterItem` of `features/ui/components/toaster`.
- Accessibility of a new or changed interaction: follow the
  `drive-accessibility-review` skill.

## Pitfalls

- **Next.js**: pages router and a static export: no server components, no API
  routes, no `getServerSideProps`.
- **Large folders**: a folder page can hold hundreds of rows. Anything read by
  every row or cell (a context value, a prop that changes on mouse move)
  re-renders them all: subscribe narrowly, as the selection store does.
- **Uploads** go from the browser straight to S3 with the `policy` returned
  by the API, then `upload-ended`: there is no upload endpoint in the backend
  to post the bytes to.
- **The SDK pages** (`src/pages/sdk/`) reuse the explorer inside another
  application: a change to a shared explorer component shows there too.
- **`react-hooks/exhaustive-deps` is off** in the ESLint configuration: the
  linter will not catch a stale closure or a missing dependency.

## Tests

- Jest with `ts-jest`, in a `__tests__/` folder next to the code
  (`*.test.ts(x)`). The environment is `node`: there is no DOM and no Testing
  Library, so tests cover pure logic (`explorer/utils/__tests__/`) and the
  driver, with `fetchAPI` mocked by `jest.mock`
  (`drivers/implementations/__tests__/StandardDriver.leaveItem.test.ts`).
- Move the logic worth testing out of the component, into a function a test
  can import.
- A rendered behaviour is covered by an E2E test, only for a user workflow
  and only when asked (see the `drive-e2e-test` skill).

## Before finishing

Run the tests of the files you changed, `yarn eslint` on them and
`yarn tsc --noEmit` (in the frontend image without yarn on the host), review
`git diff`, and add a `CHANGELOG.md` entry under `[Unreleased]` for a
user-visible change. Report what was run and what was not verified.
