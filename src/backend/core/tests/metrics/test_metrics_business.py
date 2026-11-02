"""Test the business metrics of Drive."""

from unittest import mock

from django.core.cache import cache
from django.utils import timezone

import pytest
from prometheus_client import CollectorRegistry

from core import factories, models
from core.metrics.business import CACHE_KEY, DriveBusinessCollector

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    """Each test computes its own values."""
    cache.delete(CACHE_KEY)
    yield
    cache.delete(CACHE_KEY)


def _collect():
    registry = CollectorRegistry()
    registry.register(DriveBusinessCollector())
    return {
        (sample.name, tuple(sorted(sample.labels.items()))): sample.value
        for family in registry.collect()
        for sample in family.samples
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
    assert samples[("drive_storage_used_bytes", ())] == 0


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
    assert samples[("drive_storage_used_bytes", ())] == 120


def test_metrics_business_cached(django_assert_num_queries):
    """A second scrape within the ttl should not query the database."""
    factories.UserFactory()
    _collect()

    with django_assert_num_queries(0):
        samples = _collect()

    assert samples[("drive_users_count", (("is_active", "true"),))] == 1


def test_metrics_business_failing_family_is_skipped():
    """A failing query should drop its metrics only, and nothing should be cached."""
    with mock.patch(
        "core.metrics.business.FAMILIES",
        {
            "users": mock.Mock(side_effect=RuntimeError("boom")),
            "invitations": lambda: 3,
        },
    ):
        samples = _collect()

    assert samples == {("drive_invitations_count", ()): 3}
    assert cache.get(CACHE_KEY) is None
