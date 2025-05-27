"""Test the get lock action in the WopiViewSet."""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


def test_get_lock_on_an_unlocked_file():
    """Getting a lock on an unlocked file should return 200 with empty lock header."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=folder,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    lock_service = LockService(item)
    assert lock_service.is_locked() is False

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={"X-WOPI-Override": "GET_LOCK"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-WOPI-Lock") == ""


def test_get_lock_on_a_locked_file():
    """Getting a lock on a locked file should return 200 with the lock value in header."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=folder,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    lock_service = LockService(item)
    lock_service.lock("1234567890")
    assert lock_service.is_locked() is True

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={"X-WOPI-Override": "GET_LOCK"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-WOPI-Lock") == "1234567890"
