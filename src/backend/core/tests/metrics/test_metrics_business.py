"""Test the business metrics of Drive."""

from unittest import mock

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import pytest
from prometheus_client import CollectorRegistry

from core import factories, models
from core.metrics import business
from core.metrics.business import LOCK_KEY, DriveBusinessCollector

pytestmark = pytest.mark.django_db


FRESHNESS = ("drive_business_metrics_age_seconds", "drive_business_metrics_duration_seconds")


@pytest.fixture(autouse=True)
def clear_cache():
    """Each test computes its own values."""
    cache.clear()
    yield
    cache.clear()


def _collect(freshness=False):
    """The samples of a scrape, without the age and duration of the families by default."""
    registry = CollectorRegistry()
    registry.register(DriveBusinessCollector())
    return {
        (sample.name, tuple(sorted(sample.labels.items()))): sample.value
        for family in registry.collect()
        for sample in family.samples
        if freshness or family.name not in FRESHNESS
    }


def test_metrics_business_empty_database():
    """Every metric should be there with a zero, so that dashboards have no gap."""
    samples = _collect()

    assert samples[("drive_items_count", ())] == 0
    for state in models.ItemUploadStateChoices.values:
        assert samples[(f"drive_items_{state}_count", ())] == 0
    for item_type in models.ItemTypeChoices.values:
        assert samples[(f"drive_items_{item_type}_count", ())] == 0
    assert samples[("drive_users_count", (("is_active", "true"),))] == 0
    assert samples[("drive_users_count", (("is_active", "false"),))] == 0
    assert samples[("drive_invitations_count", ())] == 0
    assert samples[("drive_accesses_count", ())] == 0


def _file(upload_state, **kwargs):
    """A file in the given upload state: a new file is always saved as pending."""
    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, **kwargs)
    models.Item.objects.filter(pk=item.pk).update(upload_state=upload_state)
    return item


def test_metrics_business_values():
    """The metrics should count what is in the database, hard deleted items aside."""
    user = factories.UserFactory()
    factories.UserFactory(is_active=False)
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, creator=user)
    _file(models.ItemUploadStateChoices.READY, size=100, creator=user)
    _file(models.ItemUploadStateChoices.ANALYZING, size=20, creator=user)
    # excluded from the quotas, but still an item
    _file(models.ItemUploadStateChoices.READY, size=1000, quota_excluded=True, creator=user)
    # hard deleted: counted nowhere
    _file(
        models.ItemUploadStateChoices.READY,
        size=5000,
        deleted_at=timezone.now(),
        hard_deleted_at=timezone.now(),
        creator=user,
    )
    factories.UserItemAccessFactory(item=folder, user=user)
    factories.InvitationFactory(item=folder)

    samples = _collect()

    assert samples[("drive_items_count", ())] == 4
    assert samples[("drive_items_folder_count", ())] == 1
    assert samples[("drive_items_file_count", ())] == 3
    assert samples[("drive_items_restriction_count", ())] == 0
    assert samples[("drive_items_ready_count", ())] == 2
    assert samples[("drive_items_analyzing_count", ())] == 1
    assert samples[("drive_items_pending_count", ())] == 0
    assert (
        samples[("drive_users_count", (("is_active", "true"),))]
        == models.User.objects.filter(is_active=True).count()
    )
    assert samples[("drive_users_count", (("is_active", "false"),))] == 1
    assert samples[("drive_invitations_count", ())] == models.Invitation.objects.count()
    assert samples[("drive_accesses_count", ())] == models.ItemAccess.objects.count()


def test_metrics_business_cached(django_assert_num_queries):
    """A second scrape within the ttl should not query the database."""
    factories.UserFactory()
    _collect()

    with django_assert_num_queries(0):
        samples = _collect()

    assert samples[("drive_users_count", (("is_active", "true"),))] == 1


def test_metrics_business_failing_family_is_skipped():
    """
    A failing family should only drop its own metrics, and should not be tried
    again before the cache ttl: a query that times out must not run at every scrape.
    """
    failing = mock.Mock(side_effect=RuntimeError("boom"))
    with mock.patch("core.metrics.business.FAMILIES", {"users": failing, "invitations": lambda: 3}):
        assert _collect() == {("drive_invitations_count", ()): 3}
        assert _collect() == {("drive_invitations_count", ()): 3}

    failing.assert_called_once()


def test_metrics_business_failing_refresh_keeps_the_previous_values(settings):
    """A family that fails to refresh should keep answering its previous values."""
    settings.PROMETHEUS_BUSINESS_METRICS_CACHE_TTL = 0
    with mock.patch("core.metrics.business.FAMILIES", {"invitations": lambda: 3}):
        _collect()
    with mock.patch(
        "core.metrics.business.FAMILIES",
        {"invitations": mock.Mock(side_effect=RuntimeError("boom"))},
    ):
        samples = _collect()

    assert samples == {("drive_invitations_count", ()): 3}


def test_metrics_business_refreshed_after_the_ttl(settings):
    """Values older than the cache ttl should be computed again."""
    settings.PROMETHEUS_BUSINESS_METRICS_CACHE_TTL = 0
    _collect()
    factories.UserFactory()

    samples = _collect()

    assert samples[("drive_users_count", (("is_active", "true"),))] == 1


def test_metrics_business_refreshed_by_one_scrape_at_a_time(settings, django_assert_num_queries):
    """
    While another scrape holds the refresh lock, a scrape should answer right away
    with the values it has, however old, without querying the database.
    """
    settings.PROMETHEUS_BUSINESS_METRICS_CACHE_TTL = 0
    _collect()
    factories.UserFactory()
    cache.add(LOCK_KEY, True, 60)

    with django_assert_num_queries(0):
        samples = _collect()

    assert samples[("drive_users_count", (("is_active", "true"),))] == 0
    # the lock belongs to the other scrape: it is left alone
    assert cache.get(LOCK_KEY) is True


def test_metrics_business_nothing_before_the_first_computation(django_assert_num_queries):
    """A scrape that cannot refresh and has no values yet should answer no family."""
    cache.add(LOCK_KEY, True, 60)

    with django_assert_num_queries(0):
        samples = _collect(freshness=True)

    assert samples == {}


def test_metrics_business_lock_released_after_a_refresh():
    """The refresh lock should be released once the families are computed."""
    with mock.patch(
        "core.metrics.business.FAMILIES",
        {"invitations": mock.Mock(side_effect=RuntimeError("boom"))},
    ):
        _collect()

    assert cache.get(LOCK_KEY) is None


def test_metrics_business_slow_query_cancelled(settings):
    """
    Postgres should cancel a query running longer than the statement timeout,
    leaving the other families and the connection usable.
    """
    settings.PROMETHEUS_BUSINESS_METRICS_STATEMENT_TIMEOUT = 0.05

    def slow():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_sleep(2)")
        return 1

    with mock.patch("core.metrics.business.FAMILIES", {"users": slow, "invitations": lambda: 3}):
        samples = _collect()

    assert samples == {("drive_invitations_count", ()): 3}
    assert models.User.objects.count() == 0


def test_metrics_business_freshness():
    """The age and the duration of every computed family should be reported."""
    samples = _collect(freshness=True)

    for family in business.FAMILIES:
        assert 0 <= samples[("drive_business_metrics_age_seconds", (("family", family),))] < 5
        assert samples[("drive_business_metrics_duration_seconds", (("family", family),))] >= 0


def _plan(run):
    """The plan of the query run() sends, with sequential scans ruled out."""
    with CaptureQueriesContext(connection) as queries:
        run()
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute(f"EXPLAIN {queries[-1]['sql']}")
        return "\n".join(row[0] for row in cursor.fetchall())


@pytest.mark.parametrize(
    "run, index",
    [
        (lambda: list(business.items_queryset()), "item_type_upload_state_idx"),
        (lambda: list(business.users_queryset()), "user_is_active_idx"),
    ],
)
def test_metrics_business_queries_use_their_index(run, index):
    """
    The counts over the large tables should be answerable from their index alone:
    a query that no longer matches it (COUNT(id), another filter) reads the whole
    item table, which takes minutes on a production sized database.
    """
    _file(models.ItemUploadStateChoices.READY, size=10)

    plan = _plan(run)

    assert f"Index Only Scan using {index}" in plan, plan
