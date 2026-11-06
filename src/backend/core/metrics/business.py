"""
Business metrics of Drive, computed from the database when the metrics are scraped.

They describe the whole deployment, not the replica that answers: every replica
reports the same values, which are to be read with max(), never summed. The
values are kept in the shared cache for PROMETHEUS_BUSINESS_METRICS_CACHE_TTL
seconds, so that the replicas and the scrapes share one set of queries.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count

from prometheus_client.core import GaugeMetricFamily

from core import models

logger = logging.getLogger(__name__)

CACHE_KEY = "metrics:business"


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


def compute_business_values():
    """
    Run the queries of every family, or take them from the cache.

    A family whose query fails is left out of the scrape, and the values are only
    cached when none failed, so that the next scrape tries again.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    results = {}
    for name, compute in FAMILIES.items():
        try:
            results[name] = compute()
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("could not compute the %s business metrics", name)

    if len(results) == len(FAMILIES):
        cache.set(CACHE_KEY, results, settings.PROMETHEUS_BUSINESS_METRICS_CACHE_TTL)
    return results


def _gauge(name, documentation, value, labels=None):
    gauge = GaugeMetricFamily(name, documentation, labels=list(labels or {}))
    gauge.add_metric(list((labels or {}).values()), value)
    return gauge


class DriveBusinessCollector:
    """Yield the business metrics, with a zero for every state nobody is in."""

    def collect(self):
        """Yield one gauge per metric of the families that could be computed."""
        values = compute_business_values()

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
