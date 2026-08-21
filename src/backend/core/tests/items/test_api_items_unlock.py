"""Tests for the item link unlock API endpoint."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_unlock_anonymous_success():
    """Anonymous users should unlock a public link with the right password."""
    item = factories.ItemFactory(link_reach="public", link_role="reader")
    item.set_link_password("s3cret")
    item.save()

    client = APIClient()
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/unlock/", {"password": "s3cret"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["abilities"]["retrieve"] is True
    assert response.json()["abilities"]["password_locked"] is False
    assert client.session["unlocked_link_items"] == [str(item.id)]

    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.status_code == 200


def test_api_items_unlock_wrong_password():
    """A wrong password should be refused and not unlock the link."""
    item = factories.ItemFactory(link_reach="public", link_role="reader")
    item.set_link_password("s3cret")
    item.save()

    client = APIClient()
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/unlock/", {"password": "wrong"}, format="json"
    )

    assert response.status_code == 403
    assert "unlocked_link_items" not in client.session

    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.status_code == 401


def test_api_items_unlock_missing_password():
    """The password field should be required."""
    item = factories.ItemFactory(link_reach="public", link_role="reader")
    item.set_link_password("s3cret")
    item.save()

    response = APIClient().post(f"/api/v1.0/items/{item.id!s}/unlock/", {}, format="json")

    assert response.status_code == 400
    assert response.json()["errors"][0]["attr"] == "password"


def test_api_items_unlock_no_password_on_link():
    """Unlocking should be refused when the link has no password."""
    item = factories.ItemFactory(link_reach="public", link_role="reader")

    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/unlock/", {"password": "s3cret"}, format="json"
    )

    assert response.status_code == 401


def test_api_items_unlock_authenticated_not_reachable():
    """Unlocking should be refused when the link does not reach the user."""
    item = factories.ItemFactory(link_reach="authenticated", link_role="reader")
    item.set_link_password("s3cret")
    item.save()

    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/unlock/", {"password": "s3cret"}, format="json"
    )

    assert response.status_code == 401


def test_api_items_unlock_explicit_access():
    """Users whose explicit access already covers the link role have nothing to unlock."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="public", link_role="reader", users=[(user, "editor")])
    item.set_link_password("s3cret")
    item.save()

    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/unlock/", {"password": "s3cret"}, format="json"
    )

    assert response.status_code == 403


def test_api_items_unlock_inherited_from_ancestor():
    """Unlocking a child should unlock the ancestor holding the password."""
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, link_reach="public")
    parent.set_link_password("s3cret")
    parent.save()
    child = factories.ItemFactory(parent=parent, link_reach=None)
    sibling = factories.ItemFactory(parent=parent, link_reach=None)

    client = APIClient()
    response = client.post(
        f"/api/v1.0/items/{child.id!s}/unlock/", {"password": "s3cret"}, format="json"
    )

    assert response.status_code == 200
    assert client.session["unlocked_link_items"] == [str(parent.id)]
    assert client.get(f"/api/v1.0/items/{sibling.id!s}/").status_code == 200


def test_api_items_unlock_throttled(settings, monkeypatch):
    """Password attempts should be rate limited."""
    monkeypatch.setitem(
        settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "items_unlock", "2/minute"
    )
    item = factories.ItemFactory(link_reach="public", link_role="reader")
    item.set_link_password("s3cret")
    item.save()

    client = APIClient()
    url = f"/api/v1.0/items/{item.id!s}/unlock/"
    assert client.post(url, {"password": "wrong"}, format="json").status_code == 403
    assert client.post(url, {"password": "wrong"}, format="json").status_code == 403
    assert client.post(url, {"password": "s3cret"}, format="json").status_code == 429
