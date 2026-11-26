# Agent Guidelines for Drive

This file contains guidelines for AI agents coding in this repository.

## Project Overview

**La Suite Drive** is a collaborative file sharing and storage application: a tree of folders and files, sharing by access or by link, online editing of office files through WOPI (Collabora, OnlyOffice), search and a trash.

Repository: https://github.com/suitenumerique/drive

## Monorepo Structure

- `src/backend/` - Django REST API (Python 3.13): `core` (main app), `wopi` (office editors), `e2e` (login without credentials for the E2E and load tests, E2E fixtures), `demo`
- `src/frontend/apps/drive/` - Main Next.js application (TypeScript, pages router, static export)
- `src/frontend/apps/e2e/` - Playwright E2E tests
- `src/frontend/packages/sdk/` - File picker SDK; `src/frontend/apps/sdk-consumer/` is its Vite demo app, used by the E2E tests
- `src/mail/` - Email templates (MJML)
- `src/helm/` - Helmfile and Helm chart
- `load-tests/` - JMeter load tests: see its README, never against production
- `docs/` - Documentation for operators and contributors (settings in `docs/env.md`)

## Development Commands

### Setup and Services

```bash
make bootstrap          # First run: build + migrate + mails + run
make build-backend      # Build the backend image
make build-frontend     # Build the frontend image and install its dependencies
make run                # Start all services
make run-backend        # Start everything but the frontend container
make stop               # Stop services
make status             # Check running services
```

### Backend (Python/Django)

Tests run inside Docker containers. You must first build the backend image and ensure the `lasuite-network` Docker network exists before running tests.

```bash
make build-backend                     # Build the backend Docker image (required before first test run)
make create-docker-network             # Create the external network (required once)
bin/pytest -n auto                     # Run all backend tests in parallel
bin/pytest -n auto path/to/test        # Run specific test file/directory
bin/pytest -n auto path/to/test.py::test_name  # Run a single test
bin/update_openapi_schema              # Regenerate core/tests/swagger/*.json after an API change
make lint                              # ruff format + ruff check --fix + pylint
make lint-ruff-format                  # Format only
make lint-ruff-check                   # Lint only
make migrate                           # Run database migrations
make makemigrations                    # Create new migrations
make resetdb                           # Flush DB + create superuser (admin@example.com/admin)
```

### Frontend (TypeScript/Next.js)

```bash
# From src/frontend/apps/drive/:
yarn dev                # Development server (port 3000)
yarn build              # Production build (type check included, no lint)
yarn lint               # ESLint (next lint)
yarn tsc --noEmit       # Type check only
yarn test               # Run Jest tests

# From project root:
make frontend-lint      # Same as yarn lint
```

Without `yarn` on the host, run the same commands in the frontend image: `docker compose exec frontend-dev yarn …` when it runs, otherwise `DOCKER_USER=$(id -u):$(id -g) docker compose run --rm frontend-dev yarn …`. E2E tests always need Node on the host (see the `drive-e2e-test` skill).

### E2E

The E2E tests need the backend on its own database (`drive_e2e`, selected by `ENV_OVERRIDE=e2e`):

```bash
make bootstrap-e2e      # Once: build the backend, migrate the e2e database, install the frontend
make run-backend-e2e    # Restart the backend on the e2e database
cd src/frontend/apps/e2e && yarn test <file> --project=chromium   # Run Playwright
make run-backend        # Back to the development database
```

### Mails and i18n

```bash
make mails-install      # Install dependencies
make mails-build        # Convert MJML to HTML + plaintext
make back-i18n-generate # Extract the backend translation strings
make back-i18n-compile  # Compile the backend translations
```

### Dev Service URLs

- Frontend: http://localhost:3000 (login `drive` / `drive`)
- Backend API/Admin: http://localhost:8071 (`admin@example.com` / `admin` after `make superuser`)
- Keycloak (auth): http://localhost:8083 (through nginx)
- RustFS (S3): http://localhost:9000, console on http://localhost:9001
- Collabora: http://localhost:9980, OnlyOffice: http://localhost:9981
- PostgreSQL: localhost:6434 (Keycloak's own database on 6433)
- Mailcatcher: http://localhost:1081

## Architecture

### Backend

- **Framework**: Django + DRF, configured via `django-configurations` (`src/backend/drive/settings.py`)
- **Main app**: `src/backend/core/` (models, API viewsets, services, authentication)
- **API**: REST on `/api/v1.0/`, mostly `ItemViewSet` (`items/` and its actions) with nested routes (`items/{id}/accesses/`, `items/{id}/invitations/`). Its OpenAPI schema is pinned by `core/tests/swagger/`
- **Auth**: OIDC via `django-lasuite` (Keycloak in dev). An optional resource server for other applications lives in `core/external_api/` (`OIDC_RESOURCE_SERVER_ENABLED`, `docs/resource_server.md`)
- **Items**: one `Item` model for folders and files. The tree is a PostgreSQL `ltree` path (`django-ltree`) whose labels are the ids of the item's ancestors and of the item itself. Deletion is soft (`deleted_at`, `ancestors_deleted_at`), then hard (`hard_deleted_at`)
- **Permissions**: `Item.get_abilities(user)` delegates to a pluggable backend (`PERMISSIONS_BACKEND`, by default `core/permissions/backends/role.py`) and is enforced by `core/api/permissions.py`. Roles and link reach are inherited along the tree
- **Restricted folders**: `Item.restrict` moves the folder to the root of the tree and leaves, under its former parent, an item of type `restriction` whose `target` is the folder. They are two distinct items: do not take one for the other in a tree, access or navigation change
- **Storage**: S3-compatible (RustFS in dev). The browser uploads a file straight to S3 (a PUT on the presigned `policy` returned by the API), then calls `items/{id}/upload-ended/`. Downloads go through nginx, which asks `items/media-auth/` before serving (`auth_request`)
- **Malware detection**: `core/malware_detection.py` moves the `upload_state` of an uploaded file
- **WOPI**: `src/backend/wopi/`, configured by `make configure-wopi` (run by `make run-backend`)
- **Entitlements and quotas**: `core/entitlements/` (`docs/entitlements.md`)
- **Search**: optional full-text indexer (`core/services/search_indexers.py`, `make index`, `docs/setup-find.md`)
- **Background tasks**: Celery + Redis (`core/tasks/`). `CELERY_TASK_ALWAYS_EAGER=True` in the `Test` configuration, so tasks run inline in tests
- **E2E endpoints**: the `e2e` app logs anyone in without credentials. `LOAD_E2E_URLS` is a literal in `settings.py`, guarded by an allowlist of configurations in `post_setup`: never make it readable from the environment

### Frontend

- **Framework**: Next.js with the pages router and a static export (`output: "export"`): no server components, no API routes
- **API access**: through the `Driver` interface (`features/drivers/Driver.ts`), obtained with `getDriver()` and implemented by `StandardDriver`. Add an endpoint there, not as a `fetchAPI` call in a component
- **State**: TanStack React Query for server state, React contexts (`GlobalExplorerContext`) for the explorer, and one external store for the selection (`docs/architecture/explorer-selection-store.md`)
- **UI**: `@gouvfr-lasuite/ui-components` (Cunningham design system), SCSS files next to the components
- **i18n**: i18next, with keys (`explorer.actions.restore.toast`), not source strings
- **Tests**: Jest (`ts-jest`, `node` environment: no DOM)

## Observability

- **Metrics**: opt-in Prometheus endpoints, guarded by a required `PROMETHEUS_API_KEY` (`docs/metrics.md`, `docs/prometheus.md`). Never put an item id, a user id or a path in a metric label
- **Sentry**: `SENTRY_DSN`

## Code Style Guidelines

### Python (Backend)
- **Formatter**: Ruff (line-length: 100)
- **Linter**: Ruff + Pylint (`make lint-pylint` runs only on files changed from `origin/main`)
- Imports (Ruff enforced): future, stdlib, django, third-party, drive (`core`, `wopi`), first-party, local
- Naming: PascalCase classes, snake_case functions/variables, UPPER_SNAKE_CASE constants
- **Print statements are forbidden** (T20 rule). The CI also searches the whole diff of a pull request, removed and context lines included, for the word print followed by an opening parenthesis, whatever the file (`.github/workflows/drive.yml` lists the few excluded paths): never write it, even in documentation
- Use `@transaction.atomic`, `select_related`/`prefetch_related`, type hints `list[str]`
- Run migrations after model changes
- In `settings.py`, `post_setup` runs after django-configurations has handed the settings to Django: change lists and dicts **in place** there (`append`, `insert`, item assignment), a reassignment is silently ignored
- A new setting is read in `drive/settings.py` and documented in `docs/env.md`
- **Tests**: Prefer the `settings` fixture from `pytest-django` over `django.test.override_settings`

### TypeScript/React (Frontend)
- **Linter**: ESLint 9 (`next/core-web-vitals`, `next/typescript`). No Prettier configuration: follow the style of the file you edit (double quotes, semicolons)
- Naming: PascalCase components/types, camelCase functions, `use*` hooks, UPPER_SNAKE_CASE constants
- Types of API objects live in `features/drivers/types.ts` and are named after the backend serializer

### Helm
- Never commit secrets

## Git Conventions

### Commit Format

```
<gitmoji>(type) lowercase title

Mandatory description explaining why.
```

- **No space** between emoji and `(type)`, **one space** after closing parenthesis
- Types: `backend`, `frontend`, `ci`, `docker`, `dependencies`, `e2e`, `wopi`, `helm`, etc.
- Gitmoji examples: `✨` feature, `🐛` fix, `♻️` refactor, `⬆️` dependency upgrade, `🔒️` security
- Commits must be signed (`-S`) and signed-off (`--signoff`). The CI lints them with gitlint and rejects `fixup!` commits
- One commit = one concern, and the tests and docs of a change go in the same commit
- Never open a pull request yourself: `CONTRIBUTING.md` leaves that to the human

### Changelog

For a change users or operators can see, update `CHANGELOG.md` under `[Unreleased]` with format: `- <gitmoji>(type) description` (less than 80 chars per line). The CI requires it on every pull request without the `noChangeLog` label, which is for the others (internal refactor, tests only).

### PR Checklist

Run before submitting: `make lint && make frontend-lint && make test`, and `yarn test` in `src/frontend/apps/drive` for a frontend change.

## General Practices

- Use DRF for REST APIs with proper serializers
- Implement proper error handling with try/except blocks
- Use Django settings for configuration
- Internationalize user-facing strings with `_()` (backend) or i18next `t()` (frontend). Frontend translations are edited by hand in `features/i18n/translations.json`: add each key to **every** language of the file (a Jest test checks it)
- Cache expensive operations, use database indexes
- Write docstrings for classes and complex functions
- Keep the comments in the code you add short and concise: explain the why, not the what

## Environment Configuration

Config files in `env.d/development/`: `common`, `postgresql`, `kc_postgresql`, `crowdin`. Create `.local` overrides (gitignored) for custom settings. With `ENV_OVERRIDE=e2e`, the `.e2e` variants replace the `.local` ones for `app-dev` and `postgresql`, and are loaded on top of them by `celery-dev`.

## Working efficiently

- Load the Skill that matches the task before exploring: it already holds the commands, helpers and pitfalls.
- Big files: grep for the symbol, then read only that range. `core/api/viewsets.py`, `core/models.py`, `core/api/serializers.py` and `drive/settings.py` are never worth reading whole. Backend tests are split per endpoint and action (`core/tests/items/test_api_items_<action>.py`), so glob for the test file.
- Never read generated or vendored files: `yarn.lock`, `uv.lock`, `core/tests/swagger/*.json`, `CHANGELOG.md` beyond its `[Unreleased]` section, `node_modules/`, `.next/`, `out/`. Grep `translations.json` for a key rather than reading it.
- Verify narrowly first and widen only once that passes: `bin/pytest -n auto <file>::<test> -x -q --tb=short` or `yarn jest <file>`, and lint only the files you touched (`yarn eslint <files>`, `docker compose run --rm --no-deps app-dev ruff check <files>`, with paths relative to `src/backend/`). Run the full `make lint` / suites once, at the end.
- Filter long command output (`| tail`, `grep`, `-q`) rather than reading it all.

## Incidental findings

While on a task, if you come across something **unrelated to it** that clearly deserves fixing (a real bug, a security issue, or a strong improvement: algorithm or SQL efficiency, documentation, CI), do not fix it or widen the task. At the end, tell the user in one or two lines (what, where, why it matters) and offer to file it with the `drive-create-issue` Skill. Only report what you verified, not style nits or guesses. A security issue is never filed as a public issue: follow `SECURITY.md`.

## Knowledge feedback

At the end of a meaningful task, consider whether you verified something repository-specific that would have saved real time or prevented a mistake had you known it at the start: a required service, a command that looks right but is not, a test-suite limitation, a helper to prefer, an invariant, a recurring failure and how to diagnose it.

Record it only if all of these hold:

- it is verified, not a guess;
- it is not already findable in this file, a Skill, a README, the Makefile, a package script or the nearby code;
- a competent developer or agent doing a similar task six months from now would be materially helped by it.

Never record facts about the current issue, temporary bugs, line numbers, branch names, one-off decisions or generic programming advice. Do not update agent documentation just to summarize the task.

Put it in the narrowest place that fits:

- **This file**: repository-wide rules and conventions that most tasks need, whatever the agent
- **An existing Skill** for the workflow it belongs to (backend, frontend, E2E tests, review, running the stack…), when your agent setup has one. Skills are versioned in `.agents/skills/<name>/SKILL.md`, the one place to edit them: `.claude/` is gitignored and `make skills` regenerates `.claude/skills/` from it, so an edit there is lost and will not show in `git diff`
- **The subsystem's own documentation** (`docs/`) when it is useful to humans too
- **A new Skill** only for a substantial, repeatable workflow with no natural home, never for a single tip

A repository fact belongs in the repository, where every agent and developer gets it, not in a personal agent memory; keep personal memory for the user's own preferences.

Prefer amending an existing line or section to adding a new one, and keep it to a line or two. Give the reason when it is not obvious. An instruction you found to be wrong is worth fixing or removing too. When in doubt, do not edit: mention it in your report instead. A human reviews the change like any code.

This file is loaded into every session, so each line costs tokens on every task. Before adding a line here, check whether it only serves one area; if so, it belongs in that area's Skill or README. Remove what has gone stale or become derivable from the code. Two Skills that trigger on the same request (a similar `description`) must be merged.

Close your report with one short line, and skip it for trivial tasks:

```text
Agent knowledge: none.
Agent knowledge: added to <file> that <fact>, because <what it would have saved>.
Agent knowledge (unverified, not recorded): <fact>.
```
