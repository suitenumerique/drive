"""Metrics of the psycopg pool of each worker process (DB_PSYCOPG_POOL_ENABLED)."""

import logging

from django.db import connections

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# The gauges are what the pool looked like at the end of the last request of
# each worker; the counters are exact, the pool counts them itself.
DATABASE_POOL_SIZE = Gauge(
    "drive_db_pool_size",
    "Connections the pools hold, idle or not",
    ["alias"],
    multiprocess_mode="livesum",
)
DATABASE_POOL_AVAILABLE = Gauge(
    "drive_db_pool_available",
    "Idle connections in the pools",
    ["alias"],
    multiprocess_mode="livesum",
)
DATABASE_POOL_REQUESTS_WAITING = Gauge(
    "drive_db_pool_requests_waiting",
    "Requests queued for a connection, all of them being taken",
    ["alias"],
    multiprocess_mode="livesum",
)
DATABASE_POOL_REQUESTS = Counter(
    "drive_db_pool_requests_total", "Connections asked to the pools", ["alias"]
)
DATABASE_POOL_REQUESTS_QUEUED = Counter(
    "drive_db_pool_requests_queued_total",
    "Connections asked to the pools that had to wait for one",
    ["alias"],
)
DATABASE_POOL_REQUESTS_WAIT_SECONDS = Counter(
    "drive_db_pool_requests_wait_seconds_total",
    "Time spent waiting for a connection of the pools",
    ["alias"],
)
DATABASE_POOL_REQUESTS_ERRORS = Counter(
    "drive_db_pool_requests_errors_total",
    "Connections asked to the pools that were not given (timeout, queue full)",
    ["alias"],
)
DATABASE_POOL_CONNECTIONS = Counter(
    "drive_db_pool_connections_total",
    "Connections the pools opened to the database",
    ["alias"],
)
DATABASE_POOL_CONNECTIONS_ERRORS = Counter(
    "drive_db_pool_connections_errors_total",
    "Connections the pools failed to open",
    ["alias"],
)


def record_database_pool(**_kwargs):
    """
    Record the state of the psycopg pools of this process. Connected to
    `request_finished`, so that it costs a request nothing while it runs.

    `pop_stats` hands the counters over and resets them, which is what lets them
    be added to ours whatever the number of worker processes.
    """
    for alias in connections:
        connection = connections[alias]
        if not connection.settings_dict.get("OPTIONS", {}).get("pool"):
            continue
        try:
            stats = connection.pool.pop_stats()
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            # a measurement never fails a request
            logger.debug("could not read the database pool stats", exc_info=True)
            continue
        DATABASE_POOL_SIZE.labels(alias).set(stats.get("pool_size", 0))
        DATABASE_POOL_AVAILABLE.labels(alias).set(stats.get("pool_available", 0))
        DATABASE_POOL_REQUESTS_WAITING.labels(alias).set(stats.get("requests_waiting", 0))
        DATABASE_POOL_REQUESTS.labels(alias).inc(stats.get("requests_num", 0))
        DATABASE_POOL_REQUESTS_QUEUED.labels(alias).inc(stats.get("requests_queued", 0))
        DATABASE_POOL_REQUESTS_WAIT_SECONDS.labels(alias).inc(
            stats.get("requests_wait_ms", 0) / 1000
        )
        DATABASE_POOL_REQUESTS_ERRORS.labels(alias).inc(stats.get("requests_errors", 0))
        DATABASE_POOL_CONNECTIONS.labels(alias).inc(stats.get("connections_num", 0))
        DATABASE_POOL_CONNECTIONS_ERRORS.labels(alias).inc(stats.get("connections_errors", 0))
