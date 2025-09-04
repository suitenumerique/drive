"""Test the unlock and relock action in the WopiViewSet."""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


def test_unlock_and_relock_without_new_lock_header():
    """Unlocking and relocking a file without a new lock header should return 400."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=folder,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
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
        headers={
            "X-WOPI-Override": "LOCK",
            "X-WOPI-OldLock": "1234567890",
        },
    )
    assert response.status_code == 400


def test_unlock_and_relock_with_mismatching_old_lock():
    """Unlocking and relocking a file with a mismatching old lock value should return 409."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=folder,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
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
            "X-WOPI-Override": "LOCK",
            "X-WOPI-OldLock": "1234567891",
            "X-WOPI-Lock": "1234567892",
        },
    )
    assert response.status_code == 409
    assert response.headers.get("X-WOPI-Lock") == "1234567890"
    assert lock_service.is_locked()
    assert lock_service.get_lock() == "1234567890"


def test_unlock_and_relock_with_matching_old_lock():
    """Unlocking and relocking a file with a matching old lock value should return 200."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=folder,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
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
            "X-WOPI-Override": "LOCK",
            "X-WOPI-OldLock": "1234567890",
            "X-WOPI-Lock": "1234567891",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-WOPI-Lock") is None
    assert lock_service.is_locked()
    assert lock_service.get_lock() == "1234567891"
