"""Tests for the grant_unlimited_storage management command."""

from io import StringIO

from django.core.management import CommandError, call_command

import pytest

from core import factories

pytestmark = pytest.mark.django_db

GB = 1000**3


def test_grants_unlimited_to_users_above_threshold():
    """Users using more than the threshold should get an unlimited storage override."""
    heavy_user = factories.UserFactory()
    factories.ItemFactory(creator=heavy_user, size=2 * GB)
    light_user = factories.UserFactory()
    factories.ItemFactory(creator=light_user, size=GB // 2)

    out = StringIO()
    call_command("grant_unlimited_storage", "--threshold-gb=1", stdout=out)

    heavy_user.refresh_from_db()
    light_user.refresh_from_db()
    assert heavy_user.storage_limit_override == 0
    assert light_user.storage_limit_override is None
    assert "Granted unlimited storage to 1 user(s)." in out.getvalue()


def test_ignores_users_at_threshold():
    """Users using exactly the threshold should not be granted unlimited storage."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=GB)

    call_command("grant_unlimited_storage", "--threshold-gb=1")

    user.refresh_from_db()
    assert user.storage_limit_override is None


def test_skips_users_with_existing_override():
    """Users with an explicit override should never be modified."""
    limited_user = factories.UserFactory(storage_limit_override=5 * GB)
    factories.ItemFactory(creator=limited_user, size=10 * GB)
    unlimited_user = factories.UserFactory(storage_limit_override=0)
    factories.ItemFactory(creator=unlimited_user, size=10 * GB)

    call_command("grant_unlimited_storage", "--threshold-gb=1")

    limited_user.refresh_from_db()
    unlimited_user.refresh_from_db()
    assert limited_user.storage_limit_override == 5 * GB
    assert unlimited_user.storage_limit_override == 0


def test_excludes_hard_deleted_and_quota_excluded_items_from_total():
    """Hard-deleted and quota excluded items should not count toward the total."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=GB // 2)
    factories.ItemFactory(creator=user, size=GB, quota_excluded=True)
    hard_deleted = factories.ItemFactory(creator=user, size=GB)
    hard_deleted.soft_delete()
    hard_deleted.hard_delete()

    call_command("grant_unlimited_storage", "--threshold-gb=1")

    user.refresh_from_db()
    assert user.storage_limit_override is None


def test_dry_run_does_not_write():
    """The dry-run mode should report the users without updating them."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=2 * GB)

    out = StringIO()
    call_command("grant_unlimited_storage", "--threshold-gb=1", "--dry-run", stdout=out)

    user.refresh_from_db()
    assert user.storage_limit_override is None
    assert f"[dry-run] Would grant unlimited storage to {user.email}" in out.getvalue()
    assert "[dry-run] Would grant unlimited storage to 1 user(s)." in out.getvalue()


def test_threshold_is_required():
    """The command should fail when no threshold is given."""
    with pytest.raises(CommandError):
        call_command("grant_unlimited_storage")
