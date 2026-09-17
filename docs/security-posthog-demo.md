# Isolated PostHog demo delivery

The demo sender sends **analyzed alerts only**, as `drive_security_alert` events.
It does not call Drive's `posthog_capture()` helper, change the global SDK client,
or reuse `POSTHOG_KEY` / `POSTHOG_HOST`. It makes bounded synchronous requests to
PostHog's batch capture API using dedicated settings. Sending defaults to off.

## Detection configuration

The sender transports the existing analyzed alert contract; it does not recompute
severity or mutate Drive permissions. The YAML configures three rule families,
including 60 downloads/minute at medium severity and 100/10 minutes at high
severity. See [rule semantics and event coverage](security-monitoring.md).

## Set up your own project

1. Create your separate demo PostHog project. Use its **project token** for capture,
   not a personal management API key. Select its ingestion origin:
   `https://eu.i.posthog.com` (EU) or `https://us.i.posthog.com` (US).
2. Copy `env.d/development/security.example` to `security.local` in the same
   directory if the local file does not already exist. The local file is ignored
   by Git and is loaded only by the two optional monitoring services.
3. Edit the local file:

```dotenv
SECURITY_DEMO_POSTHOG_ENABLED=true
SECURITY_DEMO_POSTHOG_KEY=your_demo_project_token
SECURITY_DEMO_POSTHOG_HOST=https://eu.i.posthog.com
SECURITY_DEMO_POSTHOG_BATCH_SIZE=100
SECURITY_DEMO_POSTHOG_TIMEOUT_SECONDS=10
SECURITY_MONITORING_WORKDIR=/data/security/processed-demo-v4
```

Never replace Drive's own `POSTHOG_KEY` or `POSTHOG_HOST`. If the demo token equals
Drive's configured token, the sender refuses to start. Do not commit the local
file or paste keys into screenshots. To disable sending, set the demo flag to
false and recreate the monitoring services; analysis and stdout can continue.

From the repository root, with Redis running and the development image available:

```bash
docker compose -f compose.yaml -f compose.security.yaml --profile security-monitoring up -d --no-deps --force-recreate security-worker security-beat
```

Beat schedules analysis and sending as independent tasks on our dedicated queue.
The sender can drain pending files even when the source has no new events.
A network failure does not prevent analysis from saving its results.

## One controlled demo

The fixture contains fictitious identities. Process it into a separate directory:

```bash
docker compose -f compose.yaml -f compose.security.yaml exec -T security-worker python manage.py process_security_logs --input /app/core/tests/data/security_monitoring.jsonl --workdir /data/security/posthog-smoke-v2 --batch-size 160
docker compose -f compose.yaml -f compose.security.yaml exec -T security-worker python manage.py send_security_alerts --workdir /data/security/posthog-smoke-v2
```

The fixture contains 160 events, including 120 downloads in about four minutes.
Expected: seven alerts from three families (the high download alert uses the
ten-minute condition); delivery reports `accepted` with
`sent: 7`. Repeating the send reports `caught_up`, not another seven accepted
records. The two manual commands do not require the Drive database: their database health
checks are disabled because these commands use only files and HTTP.
This manual directory is separate from the automatic source workdir.
For an independent new run, use a different workdir. The fixture has timestamps
on **2026-09-15**: include that date in PostHog's event filter and search for
`drive_security_alert`. Expand `properties` to inspect `severity`, `rule`,
`condition`, `explanation`, `recommendation` and `evidence`. No dashboard is created.

HTTP capture acknowledgement is not a read-back of the PostHog dashboard. Verify
that the expected events are visible in your project to finish the cloud check.

## Delivery guarantees and limits

Each call sends at most the configured batch size (default 100, maximum 1000)
and a bounded payload. Redirects are refused. Timeout/HTTP failure/negative
acknowledgement leave the cursor unchanged, with persistent exponential backoff
from 10 seconds to 5 minutes. Errors contain no token, payload or server body.
The sender accepts the current `{"status": "Ok"}` acknowledgement and legacy
numeric success responses. A response reporting `quota_limited` retains the
batch for retry even when the HTTP status is 200. Capture acceptance alone is
not proof that an event is visible in a dashboard.

Delivery uses `demo-posthog-state.json` and its own lock in the workdir. Analysis
and stdout retain their own independent cursors. The destination is bound to a
hash of host and token before sending. Changing projects requires a fresh workdir
and deliberate replay; it cannot silently skip events or redirect an existing
queue. There is no automatic file deletion or remote-storage retention policy.

A crash after remote acceptance but before the local cursor update can resend
identical event UUIDs, timestamps, event names and distinct IDs. PostHog deduplication
is eventual; downstream destinations can still see retries. This is not exactly-once
delivery. The sender adds `security_demo: true` and `$process_person_profile: false`,
and never sends person updates or aliases. Event timestamps remain unchanged.

The implementation uses the documented [capture API](https://posthog.com/docs/api/capture).
See also [PostHog event deduplication](https://posthog.com/docs/data/events).

## Tune through environment variables

The YAML retains readable defaults. A condition can declare `threshold_env`,
`window_seconds_env`, or `min_distinct_resources_env` naming a `SECURITY_...`
variable. A defined variable overrides that integer; invalid values fail before
processing. Examples in `security.local`:

```dotenv
SECURITY_MASS_DOWNLOAD_MINUTE_THRESHOLD=60
SECURITY_MASS_DOWNLOAD_MINUTE_WINDOW_SECONDS=60
SECURITY_MASS_DOWNLOAD_BYTES_HOUR_THRESHOLD=2000000000
SECURITY_PROBING_FIVE_MINUTES_THRESHOLD=10
SECURITY_PROBING_FIVE_MINUTES_MIN_DISTINCT_RESOURCES=5
SECURITY_PERMISSION_CHANGES_FIVE_MINUTES_MIN_DISTINCT_RESOURCES=5
```

The shipped YAML lists the remaining names. The immediate privileged self-grant
condition deliberately has no environment override. If a threshold changes, use
a new workdir and replay the source as described in the monitoring guide.
Recommendations may now be overridden per condition as well as per family.

## Producer contract

Write append-only UTF-8 **JSONL** to `data/security/events.jsonl` on the host
(`/data/security/events.jsonl` in the monitoring containers). One object per line,
newline terminated; chronological UTC timestamps with a final `Z`. Keep a stable
account ID and a globally unique event ID. Emit one event per logical operation,
not one per underlying nginx/application log line. Reusing `request_id` alone is
not sufficient when one HTTP request changes several permissions.

```json
{"id":"event-uuid","timestamp":"2026-09-16T09:00:00.000Z","actor":"user-uuid","action":"file_downloaded","resource":"file-uuid","context":{"bytes":1000000,"actor_full_name":"Demo User","request_id":"request-id"}}
```

- Mandatory engine fields: `timestamp`, `actor`, `action`.
- Integration expectations: stable `id` and `resource`; `context` object.
- Download: `context.bytes` is a nonnegative integer. The built-in producer
  records authorized full-file size, not confirmed transferred bytes; unknown
  sizes and Range requests omit it. See the producer coverage documentation.
- Display: `context.actor_full_name` optional; missing becomes null.
- Denial: `action=permission_denied`, authenticated actor and affected resource
  when known. Exclude `user_quota_exceeded`, `user_override_quota_exceeded` and
  `organization_quota_exceeded`; storage exhaustion must not feed probing counters.
  Anonymous requests, including `not_authenticated` errors, are not collected
  by these per-account rules.
- Permission change: `action=permission_changed`, plus the following context:

```json
{"target_actor":"user-uuid","old_role":"reader","new_role":"admin","actor_effective_role":"reader"}
```

Capture effective rights before mutation (for example via the existing permissions
backend / `item.get_role(actor)` before saving). A post-save lookup alone may
already return the new rights. Emit only successful committed permission changes;
rollbacks are not changes. Explicit `null` means no previous/effective access;
missing/unknown values do not prove self-escalation. If the change concerns a team,
do not substitute the team's identifier for a user self-grant.

The producer remains responsible for ordering records, preserving actor context
through mutations, and avoiding duplicate event emission. Missing sizes weaken byte
detection; missing resources weaken diversity detection. These gaps cannot be
reconstructed reliably by the engine.

## Validation and work remaining

The targeted tests cover the existing detector plus environment overrides,
inherited-role false positives, the real HTTP request body, bounded batches,
retry/resume, redirects, acknowledgement validation, configuration isolation,
and both the manual command and periodic task. HTTP tests use a local receiver
with a dummy token; they do not send to PostHog Cloud. No full application suite
is run for this change.

The built-in producer covers file authorizations, access denials, explicit
permission mutations and sharing operations. Reference workloads and an actual
local HTTP exercise are available through `make security-demo` and
`make security-demo-http`. An optional email digest is documented separately.

A project token/region and a first cloud read-back remain operator setup steps.
Representative production traffic is needed to measure false positives and recall.
Production transport, coordinated retention, direct database auditing and the
full deployment CI are separate operational work. Existing Drive product analytics
remain unchanged.
