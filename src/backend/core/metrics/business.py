"""
Business metrics of Drive, computed from the database when the metrics are scraped.

They describe the whole deployment, not the replica that answers: every replica
reports the same values, which are to be read with max(), never summed.

Each family of values is kept in the shared cache with the time it was computed.
Once older than PROMETHEUS_BUSINESS_METRICS_CACHE_TTL, the scrape that takes the
refresh lock computes it again, for all the replicas; every other scrape answers
right away with the values it has, however old. A computation that is slower
than a scrape, or than the cache ttl, therefore never runs twice at once: on a
large database, the scrapes that each started their own computation piled up
queries until the database and every gunicorn worker were busy with them.
"""

import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Count

from prometheus_client.core import GaugeMetricFamily

from core import models

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "metrics:business:"
LOCK_KEY = "metrics:business:refresh-lock"
# Values are answered until the next computation succeeds, however old: a day
# outlives any refresh, and lets a family that is no longer computed go away.
VALUES_TIMEOUT = 24 * 60 * 60


def items_queryset():
    """
    The item counts, by type and by upload state.

    COUNT(*) and not COUNT(id): the id is not in item_type_upload_state_idx, and
    counting it would read the whole item table instead of the index.
    """
    return (
        models.Item.objects.filter(hard_deleted_at__isnull=True)
        .values("type", "upload_state")
        .annotate(count=Count("*"))
        .order_by()
    )


def users_queryset():
    """The user counts, active or not, answered from user_is_active_idx."""
    return models.User.objects.values("is_active").annotate(count=Count("*")).order_by()


def _count_items():
    """Count the items that are not hard deleted, by type and by upload state."""
    counts = {"total": 0, "types": {}, "upload_states": {}}
    for row in items_queryset():
        counts["total"] += row["count"]
        counts["types"][row["type"]] = counts["types"].get(row["type"], 0) + row["count"]
        # folders have no upload state
        if row["upload_state"] is not None:
            state = row["upload_state"]
            counts["upload_states"][state] = counts["upload_states"].get(state, 0) + row["count"]
    return counts


def _count_users():
    """Count the users, active or not."""
    return {row["is_active"]: row["count"] for row in users_queryset()}


def _count_invitations():
    return models.Invitation.objects.count()


def _count_accesses():
    return models.ItemAccess.objects.count()


FAMILIES = {
    "items": _count_items,
    "users": _count_users,
    "invitations": _count_invitations,
    "accesses": _count_accesses,
}


def _cache_key(name):
    return f"{CACHE_KEY_PREFIX}{name}"


def _compute(compute):
    """
    Run the queries of a family in a transaction of their own, cancelled by
    Postgres after PROMETHEUS_BUSINESS_METRICS_STATEMENT_TIMEOUT seconds.
    """
    timeout_ms = int(settings.PROMETHEUS_BUSINESS_METRICS_STATEMENT_TIMEOUT * 1000)
    with transaction.atomic():
        with connection.cursor() as cursor:
            # SET LOCAL takes no query parameter: set_config(..., true) does the same
            cursor.execute("SELECT set_config('statement_timeout', %s, true)", [str(timeout_ms)])
        return compute()


def _refresh(names, entries):
    """
    Compute the given families again. A family that fails keeps its previous
    value, and is only tried again after the cache ttl: a query that times out
    must not run at every scrape.
    """
    for name in names:
        entry = dict(entries.get(name) or {})
        started = time.monotonic()
        try:
            entry["value"] = _compute(FAMILIES[name])
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("could not compute the %s business metrics", name)
        else:
            entry["computed_at"] = time.time()
            entry["duration"] = time.monotonic() - started
        entry["attempted_at"] = time.time()
        entries[name] = entry
        cache.set(_cache_key(name), entry, VALUES_TIMEOUT)


def compute_business_values():
    """
    The latest values of every family, refreshed first when they are too old and
    no other scrape is already refreshing them.

    Returns {family: {"value", "computed_at", "duration", "attempted_at"}} for the
    families that were computed at least once.
    """
    cached = cache.get_many([_cache_key(name) for name in FAMILIES])
    entries = {name: cached.get(_cache_key(name)) for name in FAMILIES}
    now = time.time()
    stale = [
        name
        for name, entry in entries.items()
        if now - (entry or {}).get("attempted_at", 0)
        >= settings.PROMETHEUS_BUSINESS_METRICS_CACHE_TTL
    ]

    # The lock outlives the slowest refresh: every query cancelled at the timeout
    lock_timeout = int(settings.PROMETHEUS_BUSINESS_METRICS_STATEMENT_TIMEOUT * len(stale)) + 60
    if stale and cache.add(LOCK_KEY, True, lock_timeout):
        try:
            _refresh(stale, entries)
        finally:
            cache.delete(LOCK_KEY)

    return {name: entry for name, entry in entries.items() if entry and "value" in entry}


def _gauge(name, documentation, value, labels=None):
    gauge = GaugeMetricFamily(name, documentation, labels=list(labels or {}))
    gauge.add_metric(list((labels or {}).values()), value)
    return gauge


class DriveBusinessCollector:
    """Yield the business metrics, with a zero for every state nobody is in."""

    def collect(self):
        """Yield one gauge per metric of the families that could be computed."""
        entries = compute_business_values()
        values = {name: entry["value"] for name, entry in entries.items()}

        age = GaugeMetricFamily(
            "drive_business_metrics_age_seconds",
            "Time since the values of a family of business metrics were computed",
            labels=["family"],
        )
        duration = GaugeMetricFamily(
            "drive_business_metrics_duration_seconds",
            "Time the last computation of a family of business metrics took",
            labels=["family"],
        )
        now = time.time()
        for name, entry in entries.items():
            if "computed_at" in entry:
                age.add_metric([name], now - entry["computed_at"])
                duration.add_metric([name], entry["duration"])
        yield age
        yield duration

        if (items := values.get("items")) is not None:
            yield _gauge("drive_items_count", "Items that are not hard deleted", items["total"])
            for state in models.ItemUploadStateChoices.values:
                yield _gauge(
                    f"drive_items_{state}_count",
                    f"Items in the {state} upload state",
                    items["upload_states"].get(state, 0),
                )
            for item_type in models.ItemTypeChoices.values:
                yield _gauge(
                    f"drive_items_{item_type}_count",
                    f"Items of type {item_type}",
                    items["types"].get(item_type, 0),
                )

        if (users := values.get("users")) is not None:
            gauge = GaugeMetricFamily("drive_users_count", "Users", labels=["is_active"])
            for is_active in (True, False):
                gauge.add_metric([str(is_active).lower()], users.get(is_active, 0))
            yield gauge

        if (invitations := values.get("invitations")) is not None:
            yield _gauge("drive_invitations_count", "Invitations to items", invitations)

        if (accesses := values.get("accesses")) is not None:
            yield _gauge("drive_accesses_count", "Accesses granted on items", accesses)
