# Security monitoring

An opt-in Celery worker reads normalized JSONL events, detects suspicious patterns,
and publishes actionable alerts as JSONL on stdout. Infrastructure can collect
this stream for its existing display/notifications. Local batch files support
recovery; an optional PostHog-compatible export is also written. There is no new
UI, Drive alert database, automatic PostHog sender, or automatic remediation.

## Run

From the repository root, with the existing development image, Drive and Redis
already running:

```bash
mkdir -p data/security
docker compose -f compose.yaml -f compose.security.yaml --profile security-monitoring up -d --no-deps security-worker security-beat
```

The security services are defined only in `compose.security.yaml`. The base
`compose.yaml` is unchanged. If you need another local Compose override, include
it explicitly with an additional `-f` option.

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
{"target_actor":"account-123","old_role":"reader","new_role":"admin"}
```

These fields belong inside `context`. Target must equal actor, and the new role
must exceed the old role. Supported order: no access (`null`), reader, editor,
admin, owner. An explicit `old_role: null` describes a new grant. Missing or
unknown roles cannot prove self-escalation. The other two permission predicates
count all permission changes by the acting user, including grants to others.
They detect volume requiring review, not proof of self-escalation.

A `Z` suffix does not convert local time to UTC. For an aware UTC Python datetime,
use `ts.isoformat().replace('+00:00', 'Z')`.

## Defaults and semantics

These are the team's choices from `drive-detection-thresholds.md`, not measured
production baselines or universally safe thresholds.

| Rule | OR conditions, per acting user |
| --- | --- |
| `mass_download` | 20 downloads / 60 s; 100 / 600 s; 300 / 3600 s; 2,000,000,000 recorded bytes / 3600 s |
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

The supplied brief's claim that escalation misses every single patient change
has an exception: an evidenced single self-grant to admin/owner is now detected.
No seven-day learning phase or per-user baseline is implemented. Normal-use
averages in prose must come from supplied evidence, not invented statistics.

## Alert contract

```json
{"rule":"mass_download","severity":"high","detected_at":"2026-09-15T14:32:08.000Z","window_seconds":60,"count":20,"threshold":20,"actor":{"id":"account-123","full_name":"Example User"},"explanation":"20 downloads in 60 seconds, reaching the configured threshold of 20.","recommendation":"Check whether these downloads were expected.","evidence":["event-001"]}
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
helper uses email. A separate sender needs a project host/key, delivery retries
and deduplication. JSONL files are not authenticated HTTP capture requests.

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

Explanation templates belong to conditions, recommendations to the family.
Both support `{count}`, `{window_seconds}`, `{threshold}`, `{observed_value}`,
`{distinct_resources}`, `{min_distinct_resources}`, `{actor}`, and `{action}`.
Invalid templates/configurations fail before ingestion.

Settings in `env.d/development/common.local` can override:

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
batch. Detected source replacement/truncation/rewrite requires a new work
directory after the previous stream has been drained. Never edit live state.

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

The synthetic fixture has 120 events: 20 sparse downloads, 80 rapid downloads,
15 denials and 5 self-grants. With the new defaults, it emits seven alerts:
one mass-download, one probing, five immediate self-grants. It is not a real
HTTP attack or a production false-positive measurement.

```bash
docker compose -f compose.yaml -f compose.security.yaml exec -T security-worker python manage.py process_security_logs --input /app/core/tests/data/security_monitoring.jsonl --workdir /data/security/manual-v2-01 --batch-size 120 --alerts-stdout
```

This prints alert JSONL on stdout and a processing summary on stderr. Use a new
work directory for each independent replay. Normal periodic processing already
publishes alerts automatically.

The targeted `core/tests/test_security_monitoring.py` suite checks the nine
brief predicates, windows, distinct items, bytes, custom rules, input contracts,
restart recovery, locking, stdout retries, and PostHog SDK validation with sending
disabled. The full application suite is not rerun for this update.

For contribution, follow `CONTRIBUTING.md`: title `<gitmoji>(type) lowercase title`,
a blank line and a short required body. Commit with both `--signoff` (DCO
attestation) and `-S` (SSH/GPG signature); they serve different purposes.
