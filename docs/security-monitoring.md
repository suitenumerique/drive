# Security monitoring

An opt-in Celery worker reads normalized JSONL events, detects suspicious patterns,
and publishes actionable alerts as JSONL on stdout. Infrastructure can collect
this stream for its existing display/notifications. Local batch files support
recovery; an optional PostHog-compatible export is also written. There is no new
UI, Drive alert database, or automatic remediation. A separately enabled
[demo PostHog sender](security-posthog-demo.md) can deliver the analyzed alerts.

## Run

From the repository root, with the existing development image, Drive and Redis
already running:

```bash
mkdir -p data/security
docker compose -f compose.yaml -f compose.security.yaml --profile security-monitoring up -d --no-deps --force-recreate app-dev security-worker security-beat
```

The security services and the API event producer are enabled through
`compose.security.yaml`. The base `compose.yaml` is unchanged. To enable real
Drive events, also recreate the API with the overlay (Drive's dependencies must
already be running because of `--no-deps`):

```bash
docker compose -f compose.yaml -f compose.security.yaml --profile security-monitoring up -d --no-deps --force-recreate app-dev security-worker security-beat
```

Starting only the worker/Beat does not reconfigure an existing API container.
The overlay enables `SECURITY_AUDIT_ENABLED` on `app-dev` and mounts the same
`data/security` directory there. `SECURITY_AUDIT_PATH` is the producer's path;
`SECURITY_MONITORING_INPUT` is the reader's path. Keep them aligned when changing
deployment configuration. `security.local` stays exclusive to the two monitoring
services, so the API does not receive demo PostHog credentials. If you need another
local Compose override, include it explicitly with an additional `-f` option.

The producer appends to `data/security/events.jsonl`, mounted at
`/data/security/events.jsonl` in both containers. Beat schedules a dedicated
queue every 10 seconds; one worker processes at most 100 complete lines per task.
The periodic task publishes actual alert JSONL, not only processing counters.
Celery stdout redirection is disabled for this worker, leaving diagnostics on
stderr. The collector must select stdout and parse the JSON records, ignoring
the development image entrypoint messages printed during startup.

```bash
# Human-readable inspection; Compose adds container prefixes here.
docker compose -f compose.yaml -f compose.security.yaml logs --tail=30 security-worker security-beat
# Stop only monitoring; do not use make down, which removes local database data.
docker compose -f compose.yaml -f compose.security.yaml stop security-beat security-worker
```

Only one Beat scheduler should own this schedule. Unread source records remain
on disk even if scheduled jobs expire. Monitor backlog, processing time and disk
space if input exceeds throughput. Periodic reading does not eliminate backlog.

## Event contract

UTF-8 JSONL means one JSON object per line, with a final newline. JSON arrays,
Python log prefixes and `docker compose logs` prefixes are not accepted. Raw
inputs must be chronological; equal timestamps are allowed. Required fields are
`timestamp`, `actor`, `action`. UTC ISO 8601 timestamps must end in `Z`.

```json
{"id":"event-001","timestamp":"2026-09-15T14:27:11.000Z","actor":"account-123","action":"file_downloaded","resource":"file-456","context":{"bytes":1000000,"actor_full_name":"Example User"}}
```

- `resource`: recommended resource identifier, required to establish distinct-item counts.
- `context.bytes`: optional nonnegative integer; downloaded bytes for this event.
  Missing sizes do not contribute to byte totals; known sizes may still trigger
  the byte threshold. `bytes_complete=false` marks incomplete size coverage.
- `context.actor_full_name`: optional display name; missing names become `null`,
  never an invented identity. Confirm these enrichment fields with the producer.
- `id`: recommended stable event identifier. Duplicate IDs in the active horizon
  are ignored. Without it, identity derives from stream ID and byte offset;
  copies appended at different offsets cannot be recognized as duplicates.
- `context.ip`, `user_agent`, `request_id`: accepted but not copied into alerts.

For immediate self-grant detection, a `permission_changed` event also needs:

```json
{"target_actor":"account-123","old_role":"reader","new_role":"admin","actor_effective_role":"reader"}
```

These fields belong inside `context`. Target must equal actor, and the new role
must exceed both the old local role and `actor_effective_role` (effective rights
before mutation, including inherited/team permissions). Missing effective-role
evidence skips this immediate predicate. Supported order: no access (`null`), reader, editor,
admin, owner. An explicit `old_role: null` describes a new grant. Missing or
unknown roles cannot prove self-escalation. The other two permission predicates
count all permission changes by the acting user, including grants to others.
They detect volume requiring review, not proof of self-escalation.

A `Z` suffix does not convert local time to UTC. For an aware UTC Python datetime,
use `ts.isoformat().replace('+00:00', 'Z')`.

## Implemented Drive producer

- `permission_denied`: the existing DRF exception handler records actual 403
  responses for authenticated users, including Django and DRF permission exceptions.
  Nested routes retain the item ID; media-auth retains the ID parsed before denial.
  Storage quota refusals (`user_quota_exceeded`, `user_override_quota_exceeded`,
  `organization_quota_exceeded`) keep their normal API response but emit no
  security event. Other producers must apply the same exclusion before emitting
  `permission_denied`; the engine cannot infer a quota error from that action alone.
- `file_downloaded`: a successful GET authorization in `media_auth` emits one event
  for an authenticated account. Both direct UI media links and followed download
  permalinks pass here. The redirect itself emits nothing. Preview URLs and HEAD
  checks do not count. UUID, UTC timestamp, account/resource IDs, name and request
  context follow the engine contract.

This is an **authorized file access**, not confirmation of a completed transfer.
Full-file previews using the original media URL and repeated/range requests can
still count as accesses. Known full-file sizes populate `context.bytes`, with
`bytes_semantics=authorized_file_size`; range requests and unknown sizes omit
bytes. Consequently, byte alerts from this producer describe authorized file
sizes, not measured network throughput. ZIP exports and WOPI are not collected.

Anonymous requests are excluded from per-account rules; they are not combined
under a fabricated shared identity. 401s, 404s, proxy-level denials and explicit
403 responses bypassing the exception handler are outside this collector.
`not_authenticated` is not a separate monitored action. Anonymous authentication
failures require a separately designed attribution policy and detection rule.
`context.ip` is the immediate peer address, potentially a proxy. Forwarded client
IP headers are not trusted automatically. No file contents, filenames, cookies,
authorization headers or query strings are copied into the audit event.

Collection defaults to off outside the overlay. The dedicated `monitoring_audit`
logger writes unprefixed JSONL with a POSIX file lock; the UTC timestamp is assigned
inside the lock, so concurrent writers do not reverse event order under a stable
system clock. No directory is created on settings import. Audit I/O failures leave
the API response intact and emit a diagnostic; they represent missing audit data.
Automatic rotation is deliberately absent because the current reader requires a
stable source file. Plan coordinated archival/retention before production use.

Permission and sharing operations also emit committed events:

- `permission_changed`: explicit access creation, role change, revocation and
  restoration of inherited access, including batch sharing. Context contains
  `target_actor` or `target_team`, `old_role`, `new_role` and the author's effective
  role captured before mutation. Drive's `administrator` label is normalized to
  the contract's `admin`. A new access also emits `share_created`.
- Link configuration changes emit `permission_changed`; widening the link reach
  additionally emits `share_created`. The target kind is `link`, not a person.
- New invitations emit `share_created`. Invitation updates/revocations emit
  `permission_changed` with `target_kind=invitation` and `pending=true`; these
  represent pending permission configuration, not access already held by a user.
  Email addresses are not copied into these events.

The write operations are transactional. Request attribution and prior roles are
captured before mutation; publication uses `transaction.on_commit`. Rollbacks,
no-op updates and skipped batch rows produce no successful-change event. Internal
cleanup of redundant descendant access rows is not counted as separate user
operations. Initial ownership when creating an item is not a self-escalation.
The collector deliberately instruments explicit API operations instead of attaching
request-less generic model signals. Direct SQL, administrative scripts and automatic
invitation acceptance outside these endpoints require their own attributed producer.
A legitimate API self-grant above the author's effective rights remains forbidden;
the immediate critical predicate is exercised with synthetic exploit evidence.

## Defaults and semantics

The default 60/min condition is a medium secondary signal; 100/10min is the
primary high-severity signal. Calibrate per-account bursts against representative
traffic before deployment. A platform-wide average cannot establish an individual
false-positive rate. Fixed and sliding measurement windows are not interchangeable.
Thresholds are inclusive: an isolated burst of 55 small downloads does not alert;
60 reaches the minute threshold, and 61 stays within the same alert episode.
Other conditions, such as the byte limit, are evaluated independently.

| Rule | OR conditions, per acting user |
| --- | --- |
| `mass_download` | 60 downloads / 60 s (medium); 100 / 600 s (high); 300 / 3600 s; 2,000,000,000 recorded bytes / 3600 s |
| `permission_probing` | 10 denials / 300 s on at least 5 distinct resources; 30 / 3600 s |
| `permission_escalation` | Each evidenced self-grant to admin/owner; 10 changes / 300 s on at least 5 distinct resources; 25 / 3600 s |

The three families contain nine independent conditions. Each condition may emit
its own alert; `condition` distinguishes them. For timed conditions, emit on
crossing and suppress while the predicate remains satisfied. Rearm when the
predicate becomes false on a subsequent processed event. Both window endpoints
are included. `window_seconds: 0` evaluates each event independently: each
qualifying self-grant alerts immediately. Detection uses event time, not Beat's
interval. State survives batch boundaries and worker restarts.

Downloads count operations; repeated downloads of one file count separately.
Distinct resource requirements are separate. `count` is the number of matching
events when the alert fires, not the final incident total; already published
alerts are not updated. For bytes, `threshold` and `observed_value` are in bytes,
while `count` still counts downloads. Two GB means decimal 2,000,000,000 bytes.
The short probing and permission-change predicates can trigger with count above
the threshold if the fifth distinct resource arrives later.

A single evidenced self-grant to admin/owner alerts immediately, even when no
permission-volume threshold is reached.
No seven-day learning phase or per-user baseline is implemented. Normal-use
averages in prose must come from supplied evidence, not invented statistics.

## Alert contract

```json
{"rule":"mass_download","severity":"medium","detected_at":"2026-09-15T14:32:08.000Z","window_seconds":60,"count":60,"threshold":60,"actor":{"id":"account-123","full_name":"Example User"},"explanation":"60 downloads in 60 seconds, reaching the configured threshold of 60.","recommendation":"Check whether these downloads were expected.","evidence":["event-001"]}
```

Generated alerts also contain stable `alert_id`, `condition`, `metric`,
`observed_value`, `distinct_resources`, `bytes_complete`, and
`evidence_truncated`. Evidence is limited to the first 50 matching event IDs;
counts remain exact. Keep original events so those IDs can be investigated.
`detected_at` is the timestamp of the triggering event, including when replaying
historical input; it is not the wall-clock time at which a batch ran.

Already analyzed alerts in this new contract are accepted instead of raw events
and bypass the detector. `alert_id` is recommended; all fields in the example
are required, except `actor.full_name` may be absent or null. The former alert
contract with string `actor`, `window: "300s"` and `timestamp` must be migrated.
A record containing both `action` and `rule` is rejected as ambiguous.

The optional PostHog file wraps each alert with `event=drive_security_alert`,
`distinct_id=actor.id`, `timestamp=detected_at`, `uuid=alert_id` and alert details
in `properties`. Agree on UUID/email identity mapping: Drive's current analytics
helper uses email. The optional demo sender has its own project host/key, delivery cursor and retries;
see [setup and isolation](security-posthog-demo.md). JSONL files are not authenticated HTTP capture requests.

## Change or add a rule

Edit `src/backend/core/security_rules.yaml`. It has a top-level `rules:` list.
Append a rule to count a new action without editing Python, for example:

```yaml
  - name: unusual_shares
    action: share_created
    severity: medium
    exclude_actors: []
    recommendation: "Confirm whether this sharing was authorised."
    conditions:
      - id: burst
        threshold: 20
        window_seconds: 300
        min_distinct_resources: 5
        explanation: "{count} shares on {distinct_resources} resources in {window_seconds} seconds."
```

This is an example, not a fourth shipped rule. Supported predicates combine a
count (default `metric: count`) or byte total (`metric: bytes`), window, optional
minimum distinct resources, and optional `self_grant_roles`. `exclude_actors`
contains explicit account IDs; administrators are not silently exempted. More
complex correlations still require Python. Severity is low/medium/high/critical;
a condition may override its family's severity.

Explanation templates belong to conditions; recommendations have a family default
and can be overridden by a condition. Named environment overrides are supported
for numeric thresholds, windows and minimum distinct resources; see the demo sender guide.
The two distinct-resource defaults can be overridden in `security.local`:

```dotenv
SECURITY_PROBING_FIVE_MINUTES_MIN_DISTINCT_RESOURCES=5
SECURITY_PERMISSION_CHANGES_FIVE_MINUTES_MIN_DISTINCT_RESOURCES=5
```

The immediate self-grant condition stays fixed at one evidenced event with no window.
Explanation and recommendation templates support `{count}`, `{window_seconds}`,
`{threshold}`, `{observed_value}`,
`{distinct_resources}`, `{min_distinct_resources}`, `{actor}`, and `{action}`.
Invalid templates/configurations fail before ingestion.

Settings in `env.d/development/security.local` (loaded only by the monitoring
services) can override:

```dotenv
SECURITY_MONITORING_INPUT=/data/security/events.jsonl
SECURITY_MONITORING_WORKDIR=/data/security/processed-v2
SECURITY_MONITORING_RULES=/app/core/security_rules.yaml
SECURITY_MONITORING_BATCH_SIZE=100
SECURITY_MONITORING_INTERVAL_SECONDS=10
SECURITY_MONITORING_MAX_LINE_BYTES=65536
```

After changing YAML, use a new work directory to replay the source. Existing
state intentionally refuses changed rules. To apply environment settings:

```bash
docker compose -f compose.yaml -f compose.security.yaml --profile security-monitoring up -d --no-deps --force-recreate security-worker security-beat
```

A separate mounted YAML file can be selected with `SECURITY_MONITORING_RULES`.
The rule YAML and Compose service YAML solve different problems.

## Recovery and storage

`data/security/processed/` contains `state.json` (source identity, offset and
windows), `pending.json` during a batch, `batches/*.alerts.jsonl`,
`*.posthog.jsonl` and `*.rejected.jsonl`. Rejected lines include their offset,
reason and original text. Partial trailing lines wait; oversized lines stop the
batch. Resume checks compare the resolved input path, file length, the last 128
consumed bytes and the first 4096 consumed bytes (or fewer for a short stream).
Device/inode changes alone, including Docker Desktop remounts, do not reset the
cursor or replay alerts. Legacy checkpoints acquire the head check after their
existing tail check passes. These bounded checks do not verify every byte in
the middle of a large file. A changed path or detected truncation/rewrite still
requires a new work directory after draining the previous stream. A fresh work
directory replays the input, including enabled delivery channels; do not use it
as a routine restart procedure. Never edit live state.

An atomic local journal publishes batch files before advancing the checkpoint.
The stdout publisher has its own `stdout-state.json` cursor and lock. It flushes
before advancing; after a crash it may repeat the same alert ID. Collectors must
deduplicate. A local flush is not proof of receipt by an external collector.

This spool is persistent local development storage, not a Drive database and
not tamper-proof external retention. Production infrastructure must ship logs
outside the application and configure access control and retention. Neither the
source nor output files currently have automatic rotation/cleanup. Memory grows
with events within the longest window; batch size is not a total memory cap.
A shared local/POSIX filesystem is required; this is not multi-host ingestion.

## Demo and validation

The synthetic fixture has 160 events: 20 sparse downloads, 120 downloads spaced
two seconds apart (about four minutes),
15 denials and 5 self-grants. With the new defaults, it emits seven alerts:
one high mass-download alert from the ten-minute condition, one probing, five
immediate self-grants. The download scenario stays below 60/minute. It is not a real
HTTP attack or a production false-positive measurement.

```bash
docker compose -f compose.yaml -f compose.security.yaml exec -T security-worker python manage.py process_security_logs --input /app/core/tests/data/security_monitoring.jsonl --workdir /data/security/manual-v4-01 --batch-size 160 --alerts-stdout
```

This prints alert JSONL on stdout and a processing summary on stderr. Use a new
work directory for each independent replay. Normal periodic processing already
publishes alerts automatically.

The targeted `core/tests/test_security_monitoring.py` suite checks the nine
configured predicates, windows, distinct items, bytes, custom rules, input contracts,
restart recovery, locking, stdout retries, and PostHog SDK validation with sending
disabled. `test_security_events.py` additionally exercises actual Django API calls
through JSONL to alerts and PostHog exports, plus denial variants, disabled/anonymous
collection, write failures and download exclusions. These use an isolated test
database and temporary files, without delivering events to a cloud account.
The full application suite is not rerun for this update.

For contribution, follow `CONTRIBUTING.md`: title `<gitmoji>(type) lowercase title`,
a blank line and a short required body. Commit with both `--signoff` (DCO
attestation) and `-S` (SSH/GPG signature); they serve different purposes.

## Rehearsal and local HTTP exercise

Convenience targets keep the normal Drive startup unchanged:

```bash
make security-run         # Drive dependencies must already be running
make security-status
make security-demo        # Ten synthetic repetitions; only loopback HTTP capture
make security-demo-http   # Actual local API + object storage + scheduled Celery
make security-stop        # Stops consumers; the API continues writing audit events
```

`security-demo` writes a fresh report under `data/security/rehearsals/<run>/`.
Each repetition covers an eight-hour synthetic baseline, four reference attacks,
a slow download, a distributed download and a legitimate inherited-role case.
The two evasions are expected misses and are reported separately. Delivery uses a
real local HTTP receiver with a dummy token; configured cloud credentials are
never consulted. These are reproducibility results, not production accuracy data.
Changing rule overrides can make the fixed reference expectations fail.

`security-demo-http` requires the local API, worker, Beat, PostgreSQL, Redis,
Mailcatcher and initialized MinIO storage. It refuses production mode, non-local
origins/storage, a configured Drive product-analytics token, and external SMTP.
It creates three isolated accounts with unusable passwords and ten files, then
uses a short-lived authenticated session to perform 100 file accesses, 10 denials
and 10 permission changes. The actual file content is read from object storage;
Celery must detect all three families within the timeout. The command does not
call the detector itself or weaken API authorization. The temporary session is
invalidated at completion. Demo records are retained for inspection; IDs and
results are recorded in the workdir's `http-exercises` directory.

The HTTP exercise calls media authorization and object storage directly. It does
not validate browser rendering, the reverse proxy, ZIP/WOPI coverage, or cloud
receipt. The impossible self-grant is synthetic only, not an API exploit.

## Optional email digest

The digest uses the existing Django email backend (Mailcatcher in development)
with a separate delivery cursor, independent from PostHog. It defaults to off.
Configure explicit recipients in `security.local` to schedule it:

```dotenv
SECURITY_DIGEST_ENABLED=true
SECURITY_DIGEST_RECIPIENTS=security@example.invalid
SECURITY_DIGEST_INTERVAL_SECONDS=300
```

Replace the example recipient before real deployment. Recreate worker and Beat
when changing settings. For a single local Mailcatcher delivery, without enabling
the periodic task:

```bash
docker compose -f compose.yaml -f compose.security.yaml exec -T security-worker python manage.py send_security_digest --to security-demo@example.invalid
```

Inspect the message at <http://localhost:1081>. Up to 100 pending alerts are sent
per digest, with explanations, recommendations and alert IDs. Backend failure
leaves the cursor unchanged. A crash after SMTP acceptance but before saving the
cursor can duplicate a message; this is not exactly-once delivery. Changing the
recipient set requires a fresh workdir and deliberate replay. No cloud email
integration or automatic recipient discovery is performed.
