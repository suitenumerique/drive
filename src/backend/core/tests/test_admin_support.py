"""Tests for the admin used by the support, staff users who are not superusers."""

from django.contrib.auth.models import Permission

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db

VIEW = ["view_user", "view_item"]
CHANGE = [*VIEW, "change_user"]


@pytest.fixture(autouse=True)
def static_storage(settings):
    """Serve the admin static files without their manifest."""
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


def _staff_client(client, codenames):
    """Log a staff user with the given core permissions in the client."""
    user = factories.UserFactory(is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="core", codename__in=codenames)
    )
    client.force_login(user)
    return client


def _change_data(user, **data):
    """Return the change form data of a user, overridden by the given values."""
    return {"timezone": str(user.timezone), "is_active": "on", **data}


def test_admin_support_view_no_actions(client):
    """Staff users who only view should browse the users and items without any action."""
    client = _staff_client(client, VIEW)
    user = factories.UserFactory(email="john.doe@example.com")
    target = factories.UserFactory(email="john.doe@example.com")
    item = factories.ItemFactory()

    for url in ("/admin/core/user/", "/admin/core/item/"):
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["action_form"] is None
    assert client.get(f"/admin/core/user/{user.pk}/change/").status_code == 200
    assert client.get(f"/admin/core/item/{item.pk}/change/").status_code == 200
    assert client.get(f"/admin/core/item/{item.pk}/history/").status_code == 200

    client.post(
        "/admin/core/user/",
        {"action": "merge_users", "_selected_action": [user.pk], "apply": "1", "user": target.pk},
    )
    user.refresh_from_db()
    assert user.is_active
    assert not models.UserReconciliation.objects.exists()


def test_admin_support_view_cannot_change_user(client):
    """Staff users who only view should not change a user."""
    user = factories.UserFactory()

    response = _staff_client(client, VIEW).post(
        f"/admin/core/user/{user.pk}/change/",
        _change_data(user, storage_limit_override="1"),
    )

    assert response.status_code == 403
    user.refresh_from_db()
    assert user.storage_limit_override is None


def test_admin_support_change_actions(client):
    """Staff users who change users should get the user actions only."""
    client = _staff_client(client, CHANGE)

    actions = client.get("/admin/core/user/").context["action_form"].fields["action"]
    assert [name for name, _label in actions.choices] == [
        "",
        "merge_users",
        "deactivate_duplicates",
    ]
    assert client.get("/admin/core/item/").context["action_form"] is None


def test_admin_support_change_user(client):
    """Staff users who change users should change a quota, never the permissions."""
    user = factories.UserFactory()

    response = _staff_client(client, CHANGE).post(
        f"/admin/core/user/{user.pk}/change/",
        _change_data(
            user,
            storage_limit_override="1",
            admin_email="john.doe@example.com",
            is_staff="on",
            is_superuser="on",
        ),
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.storage_limit_override == 1_000_000_000
    assert user.admin_email is None
    assert not user.is_staff
    assert not user.is_superuser


@pytest.mark.parametrize("staff", [{"is_staff": True}, {"is_superuser": True}])
def test_admin_support_change_staff(client, staff):
    """Staff users who are not superusers should not change a staff user nor its password."""
    user = factories.UserFactory(**staff)
    client = _staff_client(client, CHANGE)

    response = client.post(
        f"/admin/core/user/{user.pk}/change/", _change_data(user, storage_limit_override="1")
    )

    assert response.status_code == 403
    assert client.get(f"/admin/core/user/{user.pk}/password/").status_code == 403
    user.refresh_from_db()
    assert user.storage_limit_override is None


@pytest.mark.parametrize("action", ["merge_users"])
def test_admin_support_merge_staff(client, action):
    """Staff users who are not superusers should not merge a staff user."""
    staff = factories.UserFactory(is_superuser=True, email="john.doe@example.com")
    target = factories.UserFactory(email="john.doe@example.com")
    item = factories.ItemFactory(creator=staff, users=[(staff, "owner")])

    response = _staff_client(client, CHANGE).post(
        "/admin/core/user/",
        {"action": action, "_selected_action": [staff.pk], "apply": "1", "user": target.pk},
        follow=True,
    )

    assert "Only superusers can act on staff users." in response.content.decode()
    staff.refresh_from_db()
    item.refresh_from_db()
    assert staff.is_active
    assert item.creator == staff
    assert not models.UserReconciliation.objects.exists()


def test_admin_support_deactivate_staff(client):
    """Staff users who are not superusers should not deactivate a staff duplicate."""
    staff = factories.UserFactory(is_staff=True, email="john.doe@example.com")
    user = factories.UserFactory(email="john.doe@example.com")

    _staff_client(client, CHANGE).post(
        "/admin/core/user/",
        {"action": "deactivate_duplicates", "_selected_action": [staff.pk, user.pk]},
    )

    staff.refresh_from_db()
    user.refresh_from_db()
    assert staff.is_active
    assert user.is_active
