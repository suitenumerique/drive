"""Test the lock action in the WopiViewSet."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


def test_lock_without_lock_header():
    """Acquiring a lock without a lock header should return 400."""
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
        headers={"X-WOPI-Override": "LOCK"},
    )
    assert response.status_code == 400


def test_lock_file_on_an_unlocked_file():
    """Locking a file on an unlocked file should return 200."""
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
        headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "1234567890"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-WOPI-Lock") is None

    assert lock_service.is_locked()
    assert lock_service.get_lock() == "1234567890"


def test_lock_file_on_an_already_locked_file_with_matching_lock_header():
    """Locking a file on an already locked file with a matching lock header should return 200."""
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
    with patch.object(LockService, "refresh_lock") as mock_refresh_lock:
        response = client.post(
            f"/api/v1.0/wopi/files/{item.id}/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "1234567890"},
        )
        mock_refresh_lock.assert_called_once()
    assert response.status_code == 200
    assert response.headers.get("X-WOPI-Lock") is None

    assert lock_service.is_locked()
    assert lock_service.get_lock() == "1234567890"


def test_lock_file_on_an_already_locked_file_with_mismatching_lock_header():
    """Locking a file on an already locked file with a mismatching lock header should return 409."""
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
        headers={"X-WOPI-Override": "LOCK", "X-WOPI-Lock": "1234567891"},
    )
    assert response.status_code == 409
    assert response.headers.get("X-WOPI-Lock") == "1234567890"
    assert lock_service.is_locked()
    assert lock_service.get_lock() == "1234567890"
