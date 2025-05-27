"""Test the unlock action in the WopiViewSet."""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


def test_unlock_without_lock_header():
    """Unlocking a file without a lock header should return 400."""
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

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={"X-WOPI-Override": "UNLOCK"},
    )
    assert response.status_code == 400


def test_unlock_with_mismatching_lock():
    """Unlocking a file with a mismatching lock value should return 409."""
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
        headers={
            "X-WOPI-Override": "UNLOCK",
            "X-WOPI-Lock": "1234567891",
        },
    )
    assert response.status_code == 409
    assert response.headers.get("X-WOPI-Lock") == "1234567890"
    assert lock_service.is_locked()
    assert lock_service.get_lock() == "1234567890"


def test_unlock_with_matching_lock():
    """Unlocking a file with a matching lock value should return 200."""
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
        headers={
            "X-WOPI-Override": "UNLOCK",
            "X-WOPI-Lock": "1234567890",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-WOPI-Lock") is None
    assert not lock_service.is_locked()
