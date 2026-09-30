# Prometheus metrics

Drive ships **opt-in** Prometheus metrics, following the same contract as
[Docs](https://github.com/suitenumerique/docs/blob/main/documentation/metrics.md):
same environment variables, same `/metrics` endpoint, same bearer token and
same Helm values. They are **disabled by default**: when
`PROMETHEUS_METRICS_ENABLED` is unset, nothing is installed and `/metrics` is
a 404.

This is not the [usage metrics route](metrics.md)
(`/external_api/v1.0/metrics/usage/`), which exports per user or per
organization storage to external tools as JSON.

## Enabling it

```bash
PROMETHEUS_METRICS_ENABLED=True
PROMETHEUS_API_KEY=<a long random secret>   # or PROMETHEUS_API_KEY_FILE
```

The application **refuses to start** with the metrics enabled and no key.

Then scrape `GET /metrics` with the key as a bearer token:

```yaml
scrape_configs:
  - job_name: drive-backend
    metrics_path: /metrics
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/drive-api-key
    static_configs:
      - targets: ["drive-backend:8000"]
```

| Variable | Description | Default |
|---|---|---|
| `PROMETHEUS_METRICS_ENABLED` | Serve the metrics on `/metrics` | `False` |
| `PROMETHEUS_API_KEY` | Bearer token required on `/metrics` | `None` |
| `PROMETHEUS_METRICS_SSL_REDIRECT_EXEMPT` | Take `/metrics` out of the redirect to https, for a Prometheus scraping the pods over plain http | `False` |
| `PROMETHEUS_DB_METRICS_ENABLED` | Count and time the SQL queries | `True` |
| `PROMETHEUS_CELERY_QUEUE_METRICS_ENABLED` | Report the length of the Celery queue | `True` |
| `PROMETHEUS_BUSINESS_METRICS_ENABLED` | Report the business metrics | `True` |
| `PROMETHEUS_BUSINESS_METRICS_CACHE_TTL` | Seconds the business metrics are kept in the cache | `300` |
| `PROMETHEUS_MULTIPROC_DIR` | Directory the gunicorn workers share their metrics through | `<tmp>/drive-prometheus-<uid>` |

## What is measured

### Requests and SQL (django-prometheus)

- HTTP requests: counts and latency histograms, labelled by **view name**,
  method and status (`django_http_requests_latency_seconds_by_view_method`,
  `django_http_responses_total_by_status_view_method_total`, ...).
- SQL, unless `PROMETHEUS_DB_METRICS_ENABLED=False`: queries, errors and query
  duration (`django_db_execute_total`, `django_db_query_duration_seconds`, ...).
  The database engine is swapped for django-prometheus' instrumented subclass
  of it, only when it is the stock `django.db.backends.postgresql`.

### Database pool

With `DB_PSYCOPG_POOL_ENABLED`: `drive_db_pool_size`, `drive_db_pool_available`,
`drive_db_pool_requests_waiting`, and the counters
`drive_db_pool_requests_total`, `drive_db_pool_requests_queued_total`,
`drive_db_pool_requests_wait_seconds_total`, `drive_db_pool_requests_errors_total`,
`drive_db_pool_connections_total`, `drive_db_pool_connections_errors_total`.

### Celery queue

`drive_celery_queue_length{queue}`: tasks waiting on the default Celery queue,
asked to the broker at scrape time (Redis brokers only).

### Business metrics

Computed from the database at scrape time and kept in the shared cache for
`PROMETHEUS_BUSINESS_METRICS_CACHE_TTL` seconds. Hard deleted items are never
counted.

| Metric | Description |
|---|---|
| `drive_items_count` | Items |
| `drive_items_<state>_count` | Items per upload state: `pending`, `duplicating`, `converting`, `analyzing`, `suspicious`, `file_too_large_to_analyze`, `ready` |
| `drive_items_<type>_count` | Items per type: `file`, `folder`, `restriction` |
| `drive_users_count{is_active}` | Users, active or not |
| `drive_invitations_count` | Invitations to items |
| `drive_accesses_count` | Accesses granted on items |
| `drive_storage_used_bytes` | Size of the items counted in the quotas |

No label ever carries a path, a user or an item identifier. Every sample
carries a `hostname` label (the pod name in Kubernetes).

## Several workers, several replicas

gunicorn runs several worker processes, and a scrape is answered by one of
them. The workers write their numbers to `PROMETHEUS_MULTIPROC_DIR`, local to
the pod, and whichever answers adds them up. The gunicorn configuration
empties it when gunicorn starts and drops the gauges of the workers that are
gone.

Nothing is shared between replicas: Prometheus scrapes each pod and the
queries add them up, e.g.
`sum(rate(django_http_requests_total_by_view_transport_method_total[5m]))`.

The Celery queue and the business metrics describe the whole deployment:
every replica reports the same values. Read them with `max`, never `sum`:

```promql
max(drive_items_count)
max(drive_celery_queue_length)
```

## Kubernetes (Helm chart)

```yaml
backend:
  metrics:
    enabled: true              # PROMETHEUS_METRICS_ENABLED on the web pods, not on celery
  envVars:
    PROMETHEUS_API_KEY:
      secretKeyRef:
        name: backend
        key: PROMETHEUS_API_KEY
```

`backend.metrics.enabled` also sets `PROMETHEUS_METRICS_SSL_REDIRECT_EXEMPT`,
a pod being scraped over plain http. A value given in `backend.envVars` wins.

### Prometheus Operator, inside the cluster

```yaml
serviceMonitor:              # or podMonitor
  enabled: true
  labels:
    release: kube-prometheus-stack
```

Each backend pod is a target of its own, scraped with the bearer token read
from the Secret `PROMETHEUS_API_KEY` comes from (or the one named in
`backend.metrics.apiKeySecret`). A token that is not in a Secret is refused
at render time.

### A Prometheus outside of the cluster

```yaml
ingressMetrics:
  enabled: true
  host: metrics.drive.example.com
  annotations:
    nginx.ingress.kubernetes.io/whitelist-source-range: "203.0.113.10/32"
```

The host has to be in `ALLOWED_HOSTS`. Each scrape then lands on one replica
at random, the `hostname` label keeping their series apart: prefer the
monitors whenever the Prometheus can reach the pods.
