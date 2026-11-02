# Load tests

JMeter load-testing scenarios for the Drive backend. The goal is to measure
backend response times and error codes under load. WOPI editors and the IDP
are out of scope: authentication uses the `e2e/user-auth` endpoint (enabled
by the `LOAD_E2E_URLS` setting), like the e2e tests do.

## Scenarios

| File | Profile | Use it for |
|---|---|---|
| `drive-session.jmx` | Mixed ~50/50 read/write: every session creates a folder, uploads, deletes | Stressing the write path (uploads, deletes, storage) |
| `drive-session-read-heavy.jmx` | Read-dominant: every session browses; only `UPLOAD_PCT`% (default 15) also write | Realistic drive traffic — reads vastly outnumber writes |

Pass the scenario file as the first argument of `run.sh` (default:
`drive-session.jmx`):

```bash
./run.sh drive-session-read-heavy.jmx -JUSERS=100 -JRAMP_UP=60 -JDURATION=600
```

## Prerequisites

- Java 17+ and [Apache JMeter](https://jmeter.apache.org/) 5.6+
  (`brew install jmeter` on macOS)
- A target instance exposing the e2e auth endpoints (`LOAD_E2E_URLS`). The
  local docker compose stack has them. For a production-like target, deploy
  it with `DJANGO_CONFIGURATION=LoadTest`: this configuration is identical
  to `Production` but enables the endpoints. `LOAD_E2E_URLS` is
  intentionally not readable from the environment, and the backend refuses
  to start if it is enabled on any production configuration — a real
  production can never expose these endpoints.
- The object storage domain contained in the upload policy must be reachable
  from the machine running JMeter (uploads go straight to S3, not through
  the backend). For the local stack this is `http://localhost:9000`
  (`AWS_S3_DOMAIN_REPLACE`).

## Quick start

```bash
cd load-tests
./run.sh                                  # 5 users, 120s, against http://localhost:8071
./run.sh -JUSERS=100 -JRAMP_UP=60 -JDURATION=600
./run.sh -JBASE_URL=https://drive-load.example.com -JUSERS=500 -JRAMP_UP=300 -JDURATION=1800
```

Each run writes into `results/`, prefixed with the scenario name:

- `<scenario>-<timestamp>.jtl` — raw per-request results (CSV)
- `<scenario>-<timestamp>-report/index.html` — HTML dashboard (percentiles,
  error codes per transaction, throughput over time)

To debug or edit the scenario, open it in the GUI (`jmeter -t
drive-session.jmx`) with 1 user and a "View Results Tree" listener. Never
run an actual load from the GUI.

## Parameters

All parameters are JMeter properties, passed as `-J<NAME>=<value>` or via a
local `user.properties` file (see `user.properties.example`).

| Property | Default | Description |
|---|---|---|
| `BASE_URL` | `http://localhost:8071` | Backend base URL, no trailing slash |
| `USERS` | `5` | Number of concurrent virtual users (threads) |
| `RAMP_UP` | `5` | Seconds over which users are started |
| `DURATION` | `120` | Test duration in seconds |
| `LOOPS` | `-1` | Iterations per user (`-1` = until DURATION elapses) |
| `USER_OFFSET` | `0` | Added to the thread number to build the user email |
| `USER_EMAIL` | _(unset)_ | Log every thread in with this exact email instead of the generated `load-user-<N>@test.test` ones. Debug/smoke only: all virtual users then share one account |
| `THINK_BASE_MS` | `2000` | Minimum think time between user actions (ms) |
| `THINK_RANGE_MS` | `3000` | Random extra think time (ms), so 2–5s by default |
| `FIXTURES_DIR` | `files` | Directory whose entries are randomly uploaded |
| `UPLOAD_PCT` | `15` | Read-heavy scenario only: percentage of sessions that also upload (the first session of each user always does, to seed data) |
| `UPLOAD_ACL` | `private` | Must match the backend `AWS_S3_UPLOAD_ACL` setting |
| `CONNECT_TIMEOUT_MS` | `10000` | TCP connect timeout |
| `RESPONSE_TIMEOUT_MS` | `60000` | Response timeout |

## The mixed scenario (`drive-session.jmx`)

Each virtual user is `load-user-<USER_OFFSET + threadNum>@test.test`
(auto-created by the auth endpoint). A user logs in once — followed by the
app-shell bootstrap requests a browser fires on first page load (`00 app
bootstrap`: `GET /config/`, `GET /users/me/`, `GET /entitlements/`) — then
loops over a basic session, with think time between actions:

1. `01 list root items` — `GET /items/`
2. `02 view recents` — `GET /items/recents/` (the `/explorer/items/recent`
   page)
3. `03 view shared with me` — `GET /items/?is_creator_me=false` (the
   `/explorer/items/shared-with-me` page)
4. `04 create folder` — `POST /items/`
5. `05 open folder` — `GET /items/{id}/children/`
6. `06 upload entry` — picks ONE random top-level entry of `files/`
   (`FIXTURES_DIR`) and uploads it:
   - a plain file: `POST children` (file item) + `PUT` to object storage
     (presigned URL) + `POST upload-ended`;
   - a folder (e.g. `mon_dossier`): mirrors the frontend folder upload —
     the folder hierarchy is created first (`POST children`, parents before
     children), then every file is uploaded into its created parent with
     the same three-request sequence. Dotfiles (`.DS_Store`…) are skipped.
   The traversal is computed by `scripts/plan_upload.groovy`; the requests
   themselves are regular HTTP samplers so they appear individually in the
   report. No think time inside the upload: for a real user, dropping a
   folder is a single action.
7. `07 browse folder` — `GET /items/{id}/children/`
8. `08 move to trash` — `DELETE` the iteration folder (with its content)
9. `09 view trash` — `GET /items/trashbin/`
10. `10 empty trash` — `DELETE /items/{id}/hard-delete/` on the folder

Every request asserts its exact expected status code, so any deviation shows
up as an error with the actual code in the report. The scenario cleans up
after itself (hard-delete), so the database does not grow across runs —
except folders orphaned by iterations interrupted when the test duration
elapses, and the `load-user-*` user rows themselves.

Note: the upload policy expires 60 seconds after the file item is created
(`AWS_S3_UPLOAD_POLICY_EXPIRATION`), which is why there is deliberately no
think time inside the upload transaction.

## The read-heavy scenario (`drive-session-read-heavy.jmx`)

Same login/bootstrap and same building blocks, but the session models
realistic drive usage where reads vastly outnumber writes. With
`UPLOAD_PCT=15`, roughly 90% of transactions (and ~80% of HTTP requests,
uploads being heavy) are reads.

Every session (iteration):

1. `01 list root items`, `02 view recents`, `03 view shared with me` — as in
   the mixed scenario. The root listing also picks a random folder to visit.
2. `04 open folder` / `05 open subfolder` — navigate into the randomly
   picked folder, then into one of its subfolders (skipped when the account
   has no folder yet).

Then, only for the **first iteration of each user** (guaranteed) and for
`UPLOAD_PCT`% of the following ones:

3. `06 create folder`, `07 upload entry`, `08 browse new folder` — the write
   path of the mixed scenario. The first iteration is a **seed**: it always
   uploads the fixture folder (`mon_dossier`, a 3-level tree) and is NOT
   deleted, so later read iterations browse real data.
4. `09 move to trash`, `10 view trash`, `11 empty trash` — non-seed writes
   clean up after themselves, as in the mixed scenario.

A read-heavy run intentionally leaves data behind: the seed folders, plus
any folder orphaned by an iteration interrupted when `DURATION` elapsed.
The target instance is expected to be reset by ops (database + bucket)
between test campaigns — consecutive runs without a reset accumulate one
seed per user per run and skew comparisons.

Implementation notes:

- The write branch is an If Controller with condition
  `first iteration OR __Random(1,100) <= UPLOAD_PCT`.
- Random folder picks use the JSON extractor's random-match mode
  (`match_numbers=0`), excluding transient write folders
  (`load-<n>-<iteration>` with iteration > 0) so a folder is never browsed
  while another thread of the same account is deleting it.
- The seed pick is implemented in `scripts/plan_upload.groovy`, activated by
  the `seed_first_iteration` variable defined only by this scenario —
  `drive-session.jmx` behavior is unchanged.

## Distributed runs

`${__threadNum}` is only unique within one JMeter instance. For multiple
injector machines, give each injector a distinct `USER_OFFSET` in its local
`user.properties` (copy `user.properties.example`) so user emails stay
globally unique.

Rather than JMeter's RMI master/slave mode, prefer launching independent
injectors, each running `./run.sh` with the same `BASE_URL`/`DURATION` and
its own `USER_OFFSET`. Afterwards, merge the results and build a single
report:

```bash
# concatenate JTLs (keep the header of the first file only)
awk 'FNR==1 && NR!=1 {next} {print}' injector-*/results/*.jtl > merged.jtl
jmeter -g merged.jtl -o merged-report
```

Injector sizing rule of thumb: 1000–2000 threads per well-tuned machine.
Raise the JVM heap (`JVM_ARGS="-Xms1g -Xmx4g"`) and the open-files limit
(`ulimit -n 65535`) before large runs.

## Interpreting results

- Read p90/p95/p99 per transaction in the dashboard, not averages.
- The `06 upload entry` transaction includes the object-storage leg (the
  `PUT file to storage` samples); if it degrades while other transactions
  stay flat, look at the storage, not the backend.
- `POST upload-ended` triggers async post-processing (mimetype detection,
  previews, search indexing). Watch the Celery queue length during runs: a
  healthy API with an exploding queue is still a capacity problem.
- Reset the target instance (database + bucket) between large campaigns so
  accumulated data does not skew comparisons.
