"""Tests for the user admin class."""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, override_settings
from django.utils import timezone

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


def test_admin_users_root_items():
    """The root items the user has a direct access to should be listed with the role."""
    user = factories.UserFactory()
    workspace = factories.ItemFactory(
        title="workspace", main_workspace=True, users=[(user, "owner")]
    )
    shared = factories.ItemFactory(
        title="shared", type=models.ItemTypeChoices.FOLDER, users=[(user, "reader")]
    )
    factories.ItemFactory(title="child", parent=shared, users=[(user, "editor")])
    factories.ItemFactory(title="other-user")
    hard_deleted = factories.ItemFactory(title="hard-deleted", users=[(user, "owner")])
    hard_deleted.soft_delete()
    hard_deleted.hard_delete()

    admin_instance, loaded = _get_user(user)
    html = admin_instance.root_items(loaded)

    for item in (shared, workspace):
        assert f'href="/admin/core/item/{item.pk}/change/"' in html
    assert html.index("shared") < html.index("workspace")
    for text in ("Owner", "Reader", "main workspace"):
        assert text in html
    for title in ("child", "other-user", "hard-deleted", "Editor"):
        assert title not in html


STATIC_STORAGES = {
    **settings.STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def _admin_client(client):
    """Log a superuser in the client."""
    client.force_login(factories.UserFactory(is_staff=True, is_superuser=True))
    return client


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_duplicate_email_filter(client):
    """The filter should keep the users sharing their email, case ignored."""
    first = factories.UserFactory(email="john.doe@example.com")
    second = factories.UserFactory(email="JOHN.DOE@example.com")
    factories.UserFactory(email="jane.doe@example.com")
    factories.UserFactory(email=None)

    response = _admin_client(client).get("/admin/core/user/?duplicate_email=yes")

    assert response.status_code == 200
    assert {user.pk for user in response.context["cl"].result_list} == {first.pk, second.pk}


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_merge_users_form(client):
    """The merge action should first ask for the user to merge into."""
    user = factories.UserFactory()

    response = _admin_client(client).post(
        "/admin/core/user/",
        {"action": "merge_users", "_selected_action": [user.pk], "index": 0},
    )

    assert response.status_code == 200
    assert response.templates[0].name == "core/admin/merge_users.html"
    assert str(user.pk) in response.content.decode()


def test_admin_users_merge_users(client):
    """The merge action should move the data of the selected users and deactivate them."""
    target = factories.UserFactory(email="john.doe@example.com")
    duplicate = factories.UserFactory(email="john.doe@example.com")
    item = factories.ItemFactory(creator=duplicate, users=[(duplicate, "owner")])

    response = _admin_client(client).post(
        "/admin/core/user/",
        {
            "action": "merge_users",
            "_selected_action": [duplicate.pk, target.pk],
            "apply": "1",
            "user": target.pk,
        },
    )

    assert response.status_code == 302
    duplicate.refresh_from_db()
    item.refresh_from_db()
    assert not duplicate.is_active
    assert item.creator == target
    assert item.accesses.get().user == target
    reconciliation = models.UserReconciliation.objects.get()
    assert reconciliation.inactive_user == duplicate
    assert reconciliation.status == "done"


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_merge_users_without_email(client):
    """The merge action should refuse users without email."""
    target = factories.UserFactory(email="john.doe@example.com")
    duplicate = factories.UserFactory(email=None)

    response = _admin_client(client).post(
        "/admin/core/user/",
        {
            "action": "merge_users",
            "_selected_action": [duplicate.pk],
            "apply": "1",
            "user": target.pk,
        },
        follow=True,
    )

    assert response.status_code == 200
    assert "Users without email cannot be merged." in response.content.decode()
    assert not models.UserReconciliation.objects.exists()
    duplicate.refresh_from_db()
    assert duplicate.is_active


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_merge_users_into_inactive_user(client):
    """The merge action should refuse an inactive user as target."""
    target = factories.UserFactory(is_active=False)
    duplicate = factories.UserFactory()

    response = _admin_client(client).post(
        "/admin/core/user/",
        {
            "action": "merge_users",
            "_selected_action": [duplicate.pk],
            "apply": "1",
            "user": target.pk,
        },
    )

    assert response.status_code == 200
    assert response.templates[0].name == "core/admin/merge_users.html"
    assert list(response.context["form"].errors) == ["user"]
    assert not models.UserReconciliation.objects.exists()


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_transfer_contents_form(client):
    """The transfer action should first ask for the user to transfer to."""
    user = factories.UserFactory()

    response = _admin_client(client).post(
        "/admin/core/user/",
        {"action": "transfer_contents", "_selected_action": [user.pk], "index": 0},
    )

    assert response.status_code == 200
    assert response.templates[0].name == "core/admin/transfer_contents.html"
    assert f'value="{user.pk}"' in response.content.decode()


@pytest.mark.parametrize("keep_source_accesses", [False, True])
def test_admin_users_transfer_contents(client, keep_source_accesses):
    """The transfer action should move the items and accesses of the selected users."""
    alice, bob, carol = factories.UserFactory.create_batch(3)
    folder = factories.ItemFactory(
        creator=alice,
        type=models.ItemTypeChoices.FOLDER,
        users=[(alice, "owner"), (bob, "editor")],
    )
    file = factories.ItemFactory(creator=bob, parent=folder, type=models.ItemTypeChoices.FILE)
    shared = factories.ItemFactory(users=[(alice, "reader"), (bob, "administrator")])
    owned = factories.ItemFactory(users=[(carol, "owner"), (alice, "editor")])
    data = {
        "action": "transfer_contents",
        "_selected_action": [alice.pk, bob.pk],
        "apply": "1",
        "user": carol.pk,
    }
    if keep_source_accesses:
        data["keep_source_accesses"] = "on"

    response = _admin_client(client).post("/admin/core/user/", data)

    assert response.status_code == 302
    folder.refresh_from_db()
    file.refresh_from_db()
    assert folder.creator == file.creator == carol
    kept = {alice.pk: "owner", bob.pk: "editor"} if keep_source_accesses else {}
    assert dict(folder.accesses.values_list("user", "role")) == {**kept, carol.pk: "owner"}
    kept = {alice.pk: "reader", bob.pk: "administrator"} if keep_source_accesses else {}
    assert dict(shared.accesses.values_list("user", "role")) == {
        **kept,
        carol.pk: "administrator",
    }
    kept = {alice.pk: "editor"} if keep_source_accesses else {}
    assert dict(owned.accesses.values_list("user", "role")) == {**kept, carol.pk: "owner"}
    alice.refresh_from_db()
    assert alice.is_active


def test_admin_users_deactivate_duplicates():
    """The action should keep the most recently used user of each email."""
    now = timezone.now()
    kept = [
        factories.UserFactory(email="john.doe@example.com", last_login=now + timedelta(days=1)),
        factories.UserFactory(email="jane.doe@example.com", last_login=None),
        factories.UserFactory(email="single@example.com", last_login=None),
        factories.UserFactory(email=None, last_login=None),
        factories.UserFactory(email=None, last_login=None),
    ]
    deactivated = [
        factories.UserFactory(email="JOHN.DOE@example.com", last_login=now),
        factories.UserFactory(email="john.doe@example.com", last_login=None),
        factories.UserFactory(email="jane.doe@example.com", last_login=now),
    ]
    # Without last login, the creation date counts
    kept[1].created_at = now + timedelta(days=1)
    kept[1].save()
    request = RequestFactory().post("/")

    with mock.patch.object(UserAdmin, "message_user") as message_user:
        UserAdmin(models.User, admin.site).deactivate_duplicates(request, models.User.objects.all())

    assert set(models.User.objects.filter(is_active=True)) == set(kept)
    assert set(models.User.objects.filter(is_active=False)) == set(deactivated)
    message_user.assert_called_once_with(request, "3 users deactivated.")


def _import_storage_limits(client, content, name="limits.csv"):
    """Post a CSV file to the storage limits import view."""
    return client.post(
        "/admin/core/user/import-storage-limits/",
        {"file": SimpleUploadedFile(name, content)},
    )


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_import_storage_limits_link(client):
    """The users list should link to the storage limits import."""
    response = _admin_client(client).get("/admin/core/user/")

    assert response.status_code == 200
    assert 'href="/admin/core/user/import-storage-limits/"' in response.content.decode()


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_import_storage_limits_get(client):
    """A GET should display an empty import form without results."""
    response = _admin_client(client).get("/admin/core/user/import-storage-limits/")

    assert response.status_code == 200
    assert not response.context["form"].is_bound
    assert not response.context["form"].errors
    assert "results" not in response.context


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_import_storage_limits(client):
    """The import of the example file should set the override of every user sharing an email."""
    limited = factories.UserFactory(email="john.doe@example.com")
    duplicate = factories.UserFactory(email="john.doe@example.com", storage_limit_override=1000)
    unchanged = factories.UserFactory(email="jane.doe@example.com", storage_limit_override=0)
    default = factories.UserFactory(email="max.mustermann@example.com", storage_limit_override=1000)
    untouched = factories.UserFactory(email="untouched@example.com", storage_limit_override=1000)

    with open(finders.find("core/admin/storage_limits_example.csv"), "rb") as file:
        response = _import_storage_limits(_admin_client(client), file.read())

    assert response.status_code == 200
    assert [
        (result["email"], result.get("user"), result["status"])
        for result in response.context["results"]
    ] == [
        ("john.doe@example.com", limited, "default limit → 2.50 GB"),
        ("john.doe@example.com", duplicate, "1.00 KB → 2.50 GB"),
        ("jane.doe@example.com", unchanged, "already unlimited"),
        ("max.mustermann@example.com", default, "1.00 KB → default limit"),
        ("erika.mustermann@example.com", None, "no user found"),
    ]
    content = response.content.decode()
    assert 'href="/static/core/admin/storage_limits_example.csv"' in content
    assert f'href="/admin/core/user/{duplicate.pk}/change/"' in content
    assert "erika.mustermann@example.com" in content
    for user, expected in (
        (limited, 2_500_000_000),
        (duplicate, 2_500_000_000),
        (unchanged, 0),
        (default, None),
        (untouched, 1000),
    ):
        user.refresh_from_db()
        assert user.storage_limit_override == expected
    admin_id = response.wsgi_request.user.pk
    assert set(
        LogEntry.objects.values_list("user_id", "object_id", "action_flag", "change_message")
    ) == {
        (admin_id, str(limited.pk), CHANGE, "Storage limit imported: 2.50 GB."),
        (admin_id, str(duplicate.pk), CHANGE, "Storage limit imported: 2.50 GB."),
        (admin_id, str(default.pk), CHANGE, "Storage limit imported: default limit."),
    }


@override_settings(STORAGES=STATIC_STORAGES)
@pytest.mark.parametrize(
    "content",
    [
        b"email\njohn.doe@example.com\n",
        b"email,quota\njohn.doe@example.com,0\nnot-an-email,0\n",
        b"email,quota\njohn.doe@example.com,-1\n",
        b"email,quota\njohn.doe@example.com,abc\n",
        b"email,quota\njohn.doe@example.com,0\njohn.doe@example.com,5\n",
    ],
)
def test_admin_users_import_storage_limits_invalid_file(client, content):
    """An invalid file should be rejected without updating any user."""
    user = factories.UserFactory(email="john.doe@example.com", storage_limit_override=1000)

    response = _import_storage_limits(_admin_client(client), content)

    assert response.status_code == 200
    assert list(response.context["form"].errors) == ["file"]
    assert "results" not in response.context
    user.refresh_from_db()
    assert user.storage_limit_override == 1000


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_import_storage_limits_not_utf8(client):
    """A file not encoded in UTF-8 should be rejected with a dedicated error."""
    user = factories.UserFactory(email="john.doe@example.com", storage_limit_override=1000)

    response = _import_storage_limits(
        _admin_client(client), b"email,quota\njohn.doe@example.com,0\nren\xe9@example.com,0\n"
    )

    assert response.status_code == 200
    assert response.context["form"].errors == {"file": ["The file must be encoded in UTF-8."]}
    assert "results" not in response.context
    user.refresh_from_db()
    assert user.storage_limit_override == 1000


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_import_storage_limits_not_csv(client):
    """A file without the csv extension should be rejected."""
    user = factories.UserFactory(email="john.doe@example.com", storage_limit_override=1000)

    response = _import_storage_limits(
        _admin_client(client), b"email,quota\njohn.doe@example.com,0\n", name="limits.xlsx"
    )

    assert response.status_code == 200
    assert list(response.context["form"].errors) == ["file"]
    assert "results" not in response.context
    user.refresh_from_db()
    assert user.storage_limit_override == 1000


@override_settings(STORAGES=STATIC_STORAGES)
def test_admin_users_import_storage_limits_too_large(client):
    """A file larger than 5 MB should be rejected."""
    user = factories.UserFactory(email="john.doe@example.com", storage_limit_override=1000)
    content = b"email,quota\njohn.doe@example.com,0\n"

    response = _import_storage_limits(_admin_client(client), content.ljust(5_000_001, b"\n"))

    assert response.status_code == 200
    assert response.context["form"].errors == {"file": ["The file must not exceed 5 MB."]}
    assert "results" not in response.context
    user.refresh_from_db()
    assert user.storage_limit_override == 1000


def test_admin_users_import_storage_limits_without_change_permission(client):
    """The import should be forbidden to staff users who cannot change users."""
    user = factories.UserFactory(email="john.doe@example.com", storage_limit_override=1000)
    client.force_login(factories.UserFactory(is_staff=True))

    response = _import_storage_limits(client, b"email,quota\njohn.doe@example.com,0\n")

    assert response.status_code == 403
    user.refresh_from_db()
    assert user.storage_limit_override == 1000
