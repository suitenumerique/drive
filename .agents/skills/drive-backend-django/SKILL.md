---
name: drive-backend-django
description: Work safely and efficiently on the Django backend of La Suite Drive. Use this skill when modifying Python/Django backend code, API endpoints, serializers, permissions, models, migrations, Celery tasks, database queries, tests, or backend configuration.
---

# Drive Django backend

The backend lives in `src/backend/` and runs in the `app-dev` compose service
(mounted on `/app`, `DJANGO_CONFIGURATION=Development`, API on
http://localhost:8071). The Celery worker is `celery-dev`, on the same image.

## Commands

Use the Makefile and the `bin/` wrappers: they set the Docker user, the
environment and the configuration. Never call `python manage.py` from the host.

| task | command |
|---|---|
| start the backend services | `make run-backend` (`make status`, `make logs`) |
| management command | `./bin/manage <command>` (e.g. `./bin/manage check`) |
| migrations | `make makemigrations`, `make migrate` |
| shells | `make shell`, `make dbshell` (PostgreSQL on `localhost:6434`) |
| tests, all | `./bin/pytest -n auto` |
| tests, focused | `./bin/pytest -n auto path/to/test.py::test_name -x -q --tb=short` |
| OpenAPI schema | `./bin/update_openapi_schema` |
| lint, files you touched (paths relative to `src/backend/`) | `docker compose run --rm --no-deps app-dev ruff check core/models.py` |
| lint, all | `make lint` (ruff format, ruff check --fix, pylint) |

- `bin/pytest` runs pytest in `app-dev` with `DJANGO_CONFIGURATION=Test` and
  accepts every pytest option. Like `bin/manage`, it starts the dependencies of
  `app-dev` (PostgreSQL, Redis, RustFS, Collabora, OnlyOffice) when they are
  not running: the first run is slow.
- Keep `--no-deps` on the lint command, or it starts them too.
- `make lint` rewrites files (`ruff format`, `ruff check --fix`): review the
  diff afterwards. `make lint-pylint` only checks the files changed from
  `origin/main`, so fetch it first.
- When the backend runs on the E2E database (`make run-backend-e2e`), prefix
  the `make` and `bin/` commands with `ENV_OVERRIDE=e2e`: without it compose
  resolves the development database, not the one the backend runs on.

Run the focused tests first, then the affected module, and the full suite only
once at the end.

## Drive specifics

- **Items.** Folders and files are one model, `Item` (`type`), in a tree:
  `path` is a PostgreSQL `ltree` whose labels are the ids of the ancestors and
  of the item. Look accesses up by those ids
  (`item_id__in=str(item.path).split(".")`), not with an ancestors lookup on
  paths: see the comments of `core/permissions/backends/role.py` and
  `docs/scaling.md`.
- **Permissions** are computed by `Item.get_abilities(user)`, which delegates
  to the permissions backend (`PERMISSIONS_BACKEND`, by default
  `RolePermissionsBackend` and its `ItemAbilities`, one method per ability),
  and enforced by the classes of `core/api/permissions.py` (`ItemPermission`
  maps the action to an ability). The rights on an item come from the item
  and all its ancestors:
  - the user's accesses, direct or through a team, the highest role winning
    (`get_role`, `RoleChoices`);
  - the link reach and role (`LinkReachChoices`: restricted, authenticated,
    public; `computed_link_definition`), which can raise the role and never
    lowers it, and can be locked by a password or expired;
  - folder restrictions (`Item.is_restricted`, the `restrict` action):
    `Item.restrict` moves the folder to the root of the tree and creates,
    under its former parent, an item of type `restriction` whose `target` is
    the folder. They are two distinct items: check which one a queryset, an
    ability or a tree operation receives;
  - soft deletion: an item under a deleted ancestor (itself included)
    answers 404 to everyone but its owner, and to everyone once the trashbin
    cutoff is past.

  The abilities are serialized to the frontend, which shows or hides the
  actions from them. A new action needs its ability in `ItemAbilities.as_dict`.
- **Files** are uploaded by the browser straight to S3 with the `policy` the
  API returns, then confirmed with `upload-ended`, which checks the type and
  starts the malware detection (`upload_state`). They are served by nginx
  after a subrequest to `items/media-auth/`. Do not add a Django view that
  returns stored bytes for a download or a preview: only WOPI
  (`wopi/viewsets.py`) and the folder export stream them. Treat file names,
  extensions and mimetypes as untrusted (`core/api/utils.py`).
- **Quotas and entitlements**: `core/entitlements/`, `core/utils/quota.py`,
  `docs/entitlements.md`.
- **WOPI** (Collabora, OnlyOffice) has its own app and tests,
  `src/backend/wopi/`.
- **External API**: the viewsets of `core/external_api/` subclass the main
  ones and expose them to other applications when
  `OIDC_RESOURCE_SERVER_ENABLED` is set, for the actions listed in the
  `EXTERNAL_API` setting (`docs/resource_server.md`). A change to one of
  those actions or to a serializer changes that API too.
- **API schema**: `core/tests/swagger/` pins the OpenAPI schema. After a
  change to an endpoint or a serializer, run `./bin/update_openapi_schema` and
  commit the JSON files.
- **New setting**: read it in `drive/settings.py` and document it in
  `docs/env.md`. In `post_setup`, change lists and dicts in place, as a
  reassignment is ignored.
- **E2E fixtures** are management commands of the `e2e` app
  (`e2e/management/commands/e2e_fixture_*.py`), run by the Playwright tests.

## Tests

- Tests are split per endpoint and action:
  `core/tests/items/test_api_items_<action>.py`. Glob for the file before
  creating one, and read its neighbours to match their style.
- Build data with `core/factories.py`.
- Celery tasks run inline (`CELERY_TASK_ALWAYS_EAGER=True` in `Test`).
- Use the `settings` fixture of pytest-django, not `override_settings`.
- Pin the query count of list and detail endpoints with
  `django_assert_num_queries`, as the existing tests do.
- For a permission change, cover anonymous, authenticated without access, each
  relevant role, each link reach, and an item whose ancestor grants more.

## Checklist

- **Queries**: no N+1 or query in a loop; `select_related` and
  `prefetch_related` only where the relation is actually traversed; no
  unbounded queryset; an index for a new frequent lookup.
- **Writes**: `transaction.atomic()` around related writes; no
  check-then-create race (use a constraint or `get_or_create`); Celery tasks
  idempotent, given IDs rather than objects, and scheduled with
  `transaction.on_commit` when they depend on the transaction.
- **Authorization**: never trust the frontend; filter the queryset by what the
  user may see rather than checking after fetching; an ID from the request must
  not reach another user's object.
- **API contract**: status codes, error shape, nullable vs missing fields,
  pagination. Search the frontend (`features/drivers/`) for the endpoint
  before changing its response.
- **Migrations**: check that `makemigrations` generated only the intended
  change, and that it is safe for a rolling deployment: no long lock or table
  rewrite, no non-null column without a default on a populated table, no code
  depending on the schema before every instance has migrated. Keep large data
  migrations apart from schema changes.
- **Redis** is the cache, and through it also holds the sessions, the WOPI
  access tokens and the WOPI locks; it is the Celery broker too. Losing it
  logs everyone out and ends the open editor sessions: do not add other
  state that only lives there.

## Before finishing

Review `git diff` for unrelated changes, then report what changed, the tests
and lint actually run, and what was not verified. Never claim a check passed
without running it.
