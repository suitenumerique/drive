"""Tests for the user admin class."""

from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib import admin
from django.test import RequestFactory, override_settings

import pytest

from core import factories, models
from core.admin import UserAdmin

pytestmark = pytest.mark.django_db

LOCAL_BACKEND = "core.entitlements.backends.local.LocalEntitlementsBackend"


def _get_user(user, query=""):
    """Load a user through the admin, as its change view does."""
    admin_instance = UserAdmin(models.User, admin.site)
    request = RequestFactory().get(f"/{query}")
    return admin_instance, admin_instance.get_object(request, str(user.pk))


def _get_change_form(user, storage_limit_override=None):
    """Build the admin change form of a user, bound to a new override when given."""
    request = RequestFactory().get("/")
    request.user = factories.UserFactory(is_staff=True, is_superuser=True)
    form_class = UserAdmin(models.User, admin.site).get_form(request, user, change=True)
    form = form_class(instance=user)
    if storage_limit_override is None:
        return form
    data = {name: form[name].value() for name in form.fields}
    data = {name: value for name, value in data.items() if value is not None}
    data["storage_limit_override"] = storage_limit_override
    return form_class(data, instance=user)


@pytest.mark.parametrize(
    "override,expected",
    [(None, None), (0, 0), (20_000_000_000, 20), (1_234_567_890, Decimal("1.23456789"))],
)
def test_admin_users_storage_limit_override_shown_in_gb(override, expected):
    """The storage limit override stored in bytes should be shown in GB."""
    form = _get_change_form(factories.UserFactory(storage_limit_override=override))

    assert form.initial["storage_limit_override"] == expected


@pytest.mark.parametrize(
    "value,expected",
    [("", None), ("0", 0), ("20", 20_000_000_000), ("0.5", 500_000_000)],
)
def test_admin_users_storage_limit_override_set_in_gb(value, expected):
    """The storage limit override set in GB should be saved in bytes."""
    user = factories.UserFactory(storage_limit_override=1000)
    form = _get_change_form(user, value)

    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    assert user.storage_limit_override == expected


def test_admin_users_storage_limit_override_negative():
    """A negative storage limit override should be rejected."""
    form = _get_change_form(factories.UserFactory(), "-1")

    assert "storage_limit_override" in form.errors


def test_admin_users_storage_used():
    """The storage used should only count the user items counted in the quota."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FILE, size=100)
    factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FILE, size=20)
    factories.ItemFactory(
        creator=user, type=models.ItemTypeChoices.FILE, size=1000, quota_excluded=True
    )
    hard_deleted = factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FILE, size=1000)
    hard_deleted.soft_delete()
    hard_deleted.hard_delete()
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, size=1000)

    _admin, loaded = _get_user(user)
    _admin, loaded_without_items = _get_user(factories.UserFactory())

    assert loaded.storage_used == 120
    assert loaded_without_items.storage_used == 0


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_admin_users_storage_used_and_limit_local_backend():
    """With the local backend, the limit and the usage percentage should be shown."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FILE, size=250)

    admin_instance, loaded = _get_user(user)

    assert admin_instance.storage_used_display(loaded) == "250 B (25 %)"
    assert admin_instance.storage_limit_display(loaded) == "1.00 KB"


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_admin_users_storage_limit_override():
    """The storage limit should show the override of the user over the default limit."""
    user = factories.UserFactory(storage_limit_override=5000)

    admin_instance, loaded = _get_user(user)

    assert admin_instance.storage_limit_display(loaded) == "5.00 KB"


@pytest.mark.parametrize(
    "parameters,override",
    [
        ({"default_storage_limit": 1000}, 0),
        ({"default_storage_limit": 1000, "exempt_users_created_before": "2100-01-01"}, None),
    ],
)
def test_admin_users_storage_limit_unlimited(parameters, override):
    """An unlimited user, by override or exemption, should show the false icon as limit."""
    user = factories.UserFactory(storage_limit_override=override)

    with override_settings(
        ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
        ENTITLEMENTS_BACKEND_PARAMETERS=parameters,
        # The icon url needs no collected static files manifest
        STORAGES={
            **settings.STORAGES,
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
    ):
        admin_instance, loaded = _get_user(user)

        assert admin_instance.storage_used_display(loaded) == "0.00 B"
        assert "icon-no.svg" in admin_instance.storage_limit_display(loaded)


def test_admin_users_storage_limit_backend_without_limit():
    """A backend without storage limit should show no limit nor percentage."""
    user = factories.UserFactory()

    admin_instance, loaded = _get_user(user)

    assert admin_instance.storage_used_display(loaded) == "0.00 B"
    assert admin_instance.storage_limit_display(loaded) is None


@override_settings(
    ENTITLEMENTS_BACKEND=LOCAL_BACKEND,
    ENTITLEMENTS_BACKEND_PARAMETERS={"default_storage_limit": 1000},
)
def test_admin_users_quota_local_backend():
    """The quota should show the usage and limit given by the entitlements backend."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FILE, size=250)

    admin_instance, loaded = _get_user(user)

    assert admin_instance.quota_display(loaded) == (
        "State: default\nUsage: 250 B\nLimit: 1.00 KB\nUsed: 25 %"
    )


def test_admin_users_quota_usage_differs():
    """The storage counted by Drive should be shown when the backend usage differs."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FILE, size=250)
    admin_instance, loaded = _get_user(user)

    with mock.patch("core.admin.get_entitlements_backend") as get_backend:
        get_backend.return_value.get_quota.return_value = {
            "state": "default",
            "usage": 100,
            "limit": 1000,
        }
        assert admin_instance.quota_display(loaded) == (
            "State: default\nUsage: 100 B\nLimit: 1.00 KB\nUsed: 10 %\nCounted by Drive: 250 B"
        )


@pytest.mark.parametrize(
    "quota,expected",
    [
        ({}, "No quota\nCounted by Drive: 250 B"),
        (
            {"state": "error", "error": "metric_account_not_found"},
            "State: error\nError: metric_account_not_found\nCounted by Drive: 250 B",
        ),
        (
            {"state": "exceeded_locked", "reason": "organization_quota_exceeded"},
            "State: exceeded_locked\nReason: organization_quota_exceeded\nCounted by Drive: 250 B",
        ),
    ],
)
def test_admin_users_quota_without_limit(quota, expected):
    """A quota without limit should show its state and the storage counted by Drive."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FILE, size=250)
    admin_instance, loaded = _get_user(user)

    with mock.patch("core.admin.get_entitlements_backend") as get_backend:
        get_backend.return_value.get_quota.return_value = quota
        assert admin_instance.quota_display(loaded) == expected


def test_admin_users_top_files():
    """The biggest files of the user should be listed, biggest first, up to the limit."""
    user = factories.UserFactory()
    sizes = [10, 300, 20, 200, 100, 30]
    for size in sizes:
        factories.ItemFactory(
            creator=user, type=models.ItemTypeChoices.FILE, size=size, title=f"file-{size}.txt"
        )
    factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FOLDER, title="folder")
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, size=5000, title="other-user")
    factories.ItemFactory(
        creator=user, type=models.ItemTypeChoices.FILE, size=None, title="pending"
    )

    admin_instance, loaded = _get_user(user)
    html = admin_instance.top_files(loaded)

    titles = [f"file-{size}.txt" for size in (300, 200, 100, 30, 20)]
    positions = [html.index(title) for title in titles]
    assert positions == sorted(positions)
    for title in ("file-10.txt", "folder", "other-user", "pending"):
        assert title not in html
    for top in (5, 20, 50, 100):
        assert f'href="?top={top}"' in html


@pytest.mark.parametrize(
    "query,expected",
    [("", 5), ("?top=2", 2), ("?top=1000", 500), ("?top=0", 1), ("?top=abc", 5)],
)
def test_admin_users_top_files_limit(query, expected):
    """The top parameter should set the number of files shown, bounded and defaulted."""
    _admin, loaded = _get_user(factories.UserFactory(), query)

    assert loaded.top_files_limit == expected


def test_admin_users_top_files_flags():
    """Files in the trash or excluded from the quota should be flagged."""
    user = factories.UserFactory()
    trashed = factories.ItemFactory(
        creator=user, type=models.ItemTypeChoices.FILE, size=10, quota_excluded=True
    )
    trashed.soft_delete()

    admin_instance, loaded = _get_user(user)

    assert "in trash, excluded from quota" in admin_instance.top_files(loaded)
