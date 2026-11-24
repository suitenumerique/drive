---
name: drive-start
description: Start the La Suite Drive development stack with the least work possible. Use when asked to start, run, launch, boot or bring up Drive, the dev stack or the backend, after a clone, a pull or a branch switch. Checks what is built, stale and running, then runs only the Makefile targets needed (bootstrap only on a first run, rebuilds only the images whose dependencies changed), and copes with a frontend served by a local `yarn dev` and with a backend running on the E2E database.
---

# Start the Drive stack

The goal is a running stack for the smallest cost: some contributors have a
slow connection or little memory. `make bootstrap` and every `make build-*`
are expensive, so run them only when the check below says so. `make run` is
usually all that is needed.

## 1. Check first, change nothing

```bash
bash .agents/skills/drive-start/check-stack.sh
```

It is read-only and takes a few seconds. It reports:

- the Docker daemon, the `lasuite-network` network, the `.local` files and the
  bind-mounted directories,
- **which database the backend runs on**: the development one or the E2E one,
- **how the frontend is served**: the `frontend-dev` container, a host process
  on :3000 (a local `yarn dev`: `mode: local`), or nothing yet, and whether
  `node_modules` follows `yarn.lock`,
- each dev image: missing, stale or up to date,
- backend containers whose **dependency volume** is older than their image,
- the services' state, the database and the endpoints,
- a **suggested plan**, plus notes.

Read the plan before running it. It is a suggestion; the rules below explain
it and take precedence.

## 2. Rules behind the plan

**First run.** When no dev image and no `postgresql` container exist (a fresh
clone), run `make bootstrap`. It creates the network, the `.local` files and
the directories, builds both images, runs the migrations, builds the mails
and starts everything. Never run it on a stack that is already set up (it
rebuilds everything), nor while a local `yarn dev` holds :3000 (it starts the
frontend container, which cannot bind the port): stop the local frontend
first.

**An image is stale only when what it is built from changed.** Every dev
container bind-mounts its sources, so a change under `src/backend` or
`src/frontend` never needs a rebuild. Only these do:

| image | make target | stale when these change | services |
|---|---|---|---|
| `drive:backend-development` | `make build-backend` | `src/backend/uv.lock`, `pyproject.toml` (but for the version of the project itself), root `Dockerfile`, `docker/files/etc/mime.types`, `docker/files/usr/local/bin/entrypoint` | `app-dev`, `celery-dev` |
| `drive:frontend-development` | `make build-frontend` | `src/frontend/Dockerfile` | `frontend-dev` |

Build only the stale images, one target each. Never use `make build`: it
rebuilds both. When the frontend runs locally, never build the frontend
image.

**The frontend dependencies come from the host.** The image installs its
own, but `src/frontend/node_modules` is bind-mounted over them in
`frontend-dev`, and shared with a local `yarn dev`. After a `package.json`
or `yarn.lock` change, install them, no rebuild needed:

```bash
DOCKER_USER=<uid:gid> docker compose run --rm frontend-dev yarn install --frozen-lockfile   # container
cd src/frontend && yarn install --frozen-lockfile                                            # local
```

**The backend containers need `--renew-anon-volumes` after a rebuild.**
`/app/.venv` is an anonymous volume. `docker compose up --force-recreate`,
which is what `make run` and `make run-backend` do, carries it over to the
new container, which can therefore keep running the *old* Python
dependencies. The check reports it ("STALE dependency volume(s)"), and the
plan renews it for those services only:

```bash
DOCKER_USER=<uid:gid> docker compose up -d --force-recreate --renew-anon-volumes --no-deps app-dev celery-dev
```

- Keep `--no-deps`. Without it, a dependency recreated in the same `up` gets
  its volumes renewed too, and `kc_postgresql` keeps the Keycloak realm in an
  anonymous volume.
- Each renewal leaves the old volume dangling. `docker volume ls -f
  dangling=true` lists them. Suggest a cleanup to the user; never prune
  yourself.
- Always pass `DOCKER_USER` as the plan prints it. Without it, compose runs
  the containers as `1000` and the bind-mounted files can become unwritable.

**The check is a heuristic.** A manifest or a build file is only compared
when its modification time is newer than the image, and a dependency volume
is judged on its creation date, not on what it holds. "up to date" and "ok"
are therefore not proofs: when a container fails on a missing module or an
old dependency while the check sees nothing, rebuild the image and renew
the volume anyway. A build file edited but not committed when the image was
built shows as changed: the rebuild is then optional.

**The E2E database.** `make run-backend-e2e` runs the same services on the
`drive_e2e` database (`ENV_OVERRIDE=e2e`, data in `data/postgresql.e2e`).
The check reads the mode from the `app-dev` and `postgresql` containers,
stopped ones included, so a stack stopped on the E2E database is still
reported as such. When the check says `mode: e2e`, every command of the plan carries
`ENV_OVERRIDE=e2e`: keep it, or the container is recreated on the development
database. `make run-backend` and `make run` switch back to the development
database: say so before running them, and do it only when the user wants the
development stack. Asked to start the stack *for the E2E tests*, follow the
`drive-e2e-test` skill instead.

**The frontend.**

- `mode: local`: something already answers on :3000 from the host, usually
  the user's own `yarn dev`. This is expected. Run `make run-backend`, not
  `make run`: `make run` would try to start the `frontend-dev` container and
  fail with "port 3000 is already allocated". Tell the user the frontend on
  :3000 is theirs and was left alone.
- `mode: undecided`: nothing on :3000 and yarn is installed. Ask the user
  whether to run the frontend locally or in Docker.
  - Locally: `make run-backend`, then `make run-frontend-development`. That
    target blocks, so start it with `run_in_background`. It stops the
    container and runs `yarn dev`.
  - In Docker: build the frontend image if it is missing or stale, then run
    `make run`.
- `mode: container`: `make run`.
- Never install yarn to start the stack.

**Already up.** When every backend service is running and answering, the plan
skips `make run`/`make run-backend` and only recreates what changed: those
targets force-recreate the containers for nothing. With nothing to change,
the plan says so. Report that and stop.

**Database.**

- `make migrate` when migrations are pending or the database is empty.
- The PostgreSQL data lives in `data/postgresql.local`, on the host: stopping
  or removing the containers keeps it.

## 3. Run the plan

- Use the Bash tool from the repository root and the Makefile targets as
  written.
- Builds and `make bootstrap` can exceed the 2-minute default. Pass
  `timeout: 600000`, or use `run_in_background` for `make bootstrap`.
- The first start is slow: `app-dev` waits for Collabora and OnlyOffice to be
  healthy, which can take a minute or two.
- Before `make bootstrap`, a rebuild, or anything else long, tell the user in
  one line what you are about to run and why ("backend image stale:
  `uv.lock` changed").
- Never run `make down`, `make clean`, `make resetdb`, `make demo`, `docker
  compose down`, `docker system prune` or `--no-cache` builds to "start
  clean". `make down` deletes `data/postgresql.*`, the databases included;
  the others lose data or the build cache.

## 4. Verify, then report

Run `check-stack.sh` again. The endpoints must answer `200` and the plan must
say "Nothing to do". Then give the user a short summary:

- what was run, and why,
- the URLs: frontend http://localhost:3000, API/admin http://localhost:8071,
  Keycloak http://localhost:8083, mails http://localhost:1081, RustFS
  http://localhost:9001,
- the logins: `drive` / `drive` for the app (Keycloak); `admin@example.com`
  / `admin` for the Django admin once `make superuser` has run,
- the notes from the check (local frontend, E2E database, drifted
  `node_modules`).

## Troubleshooting

- **A service keeps restarting**: `docker compose logs --tail 80 <service>`.
  If the traceback shows a missing module after a pull, the dependencies are
  stale. The check tells whether the image or only the volume is behind.
- **`env file ... .local not found`**: run `make create-dev-local-files`.
- **Edits to `docker/auth/realm.json` have no effect**: Keycloak imports the
  realm only once, and its `kc_postgresql` keeps it in an anonymous volume.
  Run `docker compose rm -sfv keycloak kc_postgresql && docker compose up -d
  keycloak`. Everyone will have to log in again, and whatever was changed in
  Keycloak since the import (users, clients) is lost: warn the user first.
- **The Docker daemon is not reachable**: ask the user to start Docker. Do
  not try to start it yourself.

## Improvements

Whenever you notice something that would make starting the stack cheaper or
more reliable, tell the user and **ask before proposing a change**. This
covers:

- the Makefile: a target that does too much, a missing guard, a non-idempotent
  step,
- `compose.yaml` or the Dockerfiles,
- this skill or `check-stack.sh`: a false positive or negative in the
  staleness check, a new service, a new image, a new `.local` file.

Keep the image table above and the `IMAGES` list in `check-stack.sh` in step
with `compose.yaml` and the Dockerfiles.
