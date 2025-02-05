"""Test related to item upload ended API."""

import pytest
from rest_framework.test import APIClient

from core import factories
from core.models import ItemTypeChoices, ItemUploadStateChoices

pytestmark = pytest.mark.django_db


def test_api_item_upload_ended_anonymous():
    """Anonymous users should not be allowed to end an upload."""
    item = factories.ItemFactory()
    response = APIClient().post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 401


@pytest.mark.parametrize("role", [None, "reader", "editor"])
def test_api_item_upload_ended_no_permissions(role):
    """Users without write permissions should not be allowed to end an upload."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()

    if role:
        factories.UserItemAccessFactory(item=item, user=user, role=role)

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "item_type", [t[0] for t in ItemTypeChoices.choices if t[0] != ItemTypeChoices.FILE]
)
def test_api_item_upload_ended_on_none_file_item(item_type):
    """Users should not be allowed to end an upload on items that are not files."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=item_type)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.json() == {
        "item": "This action is only available for items of type FILE."
    }
    assert response.status_code == 400


def test_api_item_upload_ended_on_wrong_upload_state():
    """
    Users should not be allowed to end an upload on items that are not in the PENDING upload state.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE)
    item.upload_state = ItemUploadStateChoices.UPLOADED
    item.save()
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 400
    assert response.json() == {
        "item": "This action is only available for items in PENDING state."
    }


def test_api_item_upload_ended_success():
    """
    Users should be able to end an upload on items that are files and in the UPLOADING upload state.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 200

    item.refresh_from_db()
    assert item.upload_state == ItemUploadStateChoices.UPLOADED
