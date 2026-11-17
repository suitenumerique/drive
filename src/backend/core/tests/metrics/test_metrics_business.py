"""Test the business metrics of Drive."""

from unittest import mock

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import pytest
from lasuite.malware_detection.models import MalwareDetection, MalwareDetectionStatus
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

    assert samples[("drive_users_count", (("is_active", "true"),))] == 0
    assert samples[("drive_users_count", (("is_active", "false"),))] == 0
    assert samples[("drive_invitations_count", ())] == 0
    assert samples[("drive_accesses_count", ())] == 0
    for status in MalwareDetectionStatus.values:
        assert samples[("drive_malware_detections", (("status", status),))] == 0
    for status in ("pending", "processing"):
        assert samples[("drive_malware_detection_oldest_age_seconds", (("status", status),))] == 0
    assert ("drive_malware_detection_oldest_age_seconds", (("status", "failed"),)) not in samples


def _detection(status, age):
    """A malware detection created `age` ago: created_at is set on creation."""
    detection = MalwareDetection.objects.create(
        path=f"item/{timezone.now().timestamp()}/file.txt", status=status, backend="test"
    )
    MalwareDetection.objects.filter(pk=detection.pk).update(
        created_at=timezone.now() - timezone.timedelta(seconds=age)
    )
    return detection


def test_metrics_business_malware_detections():
    """
    The malware detection queue should be counted by status, with how long its
    oldest pending and processing detections have been waiting.
    """
    _detection(MalwareDetectionStatus.PENDING, age=600)
    _detection(MalwareDetectionStatus.PENDING, age=30)
    _detection(MalwareDetectionStatus.PROCESSING, age=120)
    _detection(MalwareDetectionStatus.FAILED, age=86400)
    _detection(MalwareDetectionStatus.FAILED, age=60)
    _detection(MalwareDetectionStatus.FAILED, age=10)

    samples = _collect()

    assert samples[("drive_malware_detections", (("status", "pending"),))] == 2
    assert samples[("drive_malware_detections", (("status", "processing"),))] == 1
    assert samples[("drive_malware_detections", (("status", "failed"),))] == 3
    pending_age = samples[("drive_malware_detection_oldest_age_seconds", (("status", "pending"),))]
    processing_age = samples[
        ("drive_malware_detection_oldest_age_seconds", (("status", "processing"),))
    ]
    assert 600 <= pending_age < 610
    assert 120 <= processing_age < 130
    # how long the failed detections have waited means nothing: they wait no more
    assert ("drive_malware_detection_oldest_age_seconds", (("status", "failed"),)) not in samples


def test_metrics_business_malware_detections_own_ttl(settings):
    """
    The malware detection queue should be computed again after its own cache ttl,
    while the other families keep their cached values.
    """
    settings.PROMETHEUS_BUSINESS_METRICS_CACHE_TTL = 300
    settings.PROMETHEUS_MALWARE_DETECTION_METRICS_CACHE_TTL = 0
    _collect()
    factories.UserFactory()
    _detection(MalwareDetectionStatus.PENDING, age=0)

    samples = _collect()

    assert samples[("drive_malware_detections", (("status", "pending"),))] == 1
    assert samples[("drive_users_count", (("is_active", "true"),))] == 0


def test_metrics_business_values():
    """The metrics should count what is in the database."""
    user = factories.UserFactory()
    factories.UserFactory(is_active=False)
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, creator=user)
    factories.UserItemAccessFactory(item=folder, user=user)
    factories.InvitationFactory(item=folder)

    samples = _collect()

    assert not any(name.startswith("drive_items_") for name, _labels in samples)
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
        (lambda: list(business.users_queryset()), "user_is_active_idx"),
    ],
)
def test_metrics_business_queries_use_their_index(run, index):
    """
    The counts should be answerable from their index alone: a query that no
    longer matches it (COUNT(id), another filter) reads the whole table, and
    keeps getting slower as the table grows.
    """
    factories.UserFactory()

    plan = _plan(run)

    assert f"Index Only Scan using {index}" in plan, plan
