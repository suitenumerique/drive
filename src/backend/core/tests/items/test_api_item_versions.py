"""Tests for the item versions API endpoint."""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


def _make_item_with_versions(user, **item_kwargs):
    """An item currently on blob_v2, with two versions (v1 on blob_v1, v2 current)."""
    blob_v1 = factories.BlobFactory(hash="1" * 64, size=10)
    blob_v2 = factories.BlobFactory(hash="2" * 64, size=20)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="doc.txt",
        blob=blob_v2,
        mimetype="text/plain",
        update_upload_state=models.ItemUploadStateChoices.READY,
        **item_kwargs,
    )
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    v1 = factories.ItemVersionFactory(
        item=item, blob=blob_v1, filename="doc.txt", mimetype="text/plain", author=user
    )
    v2 = factories.ItemVersionFactory(
        item=item, blob=blob_v2, filename="doc.txt", mimetype="text/plain", author=user
    )
    return item, v1, v2


def test_api_item_versions_list_explicit_access():
    """A user with an explicit access lists the versions, current one flagged."""
    user = factories.UserFactory()
    item, v1, v2 = _make_item_with_versions(user)

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/versions/")

    assert response.status_code == 200
    versions = response.json()
    assert {v["id"] for v in versions} == {str(v1.id), str(v2.id)}
    current = [v for v in versions if v["is_current"]]
    assert len(current) == 1
    assert current[0]["id"] == str(v2.id)
    assert current[0]["size"] == 20


def test_api_item_versions_list_link_only_access_denied():
    """A user granted only through a share link cannot list versions."""
    user = factories.UserFactory()
    item, _, _ = _make_item_with_versions(
        factories.UserFactory(), link_reach=models.LinkReachChoices.AUTHENTICATED
    )

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/versions/")

    assert response.status_code == 403


def test_api_item_versions_list_anonymous_denied():
    """Anonymous users cannot list versions."""
    item, _, _ = _make_item_with_versions(
        factories.UserFactory(), link_reach=models.LinkReachChoices.PUBLIC
    )

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/versions/")

    assert response.status_code in (401, 403)


def test_api_item_versions_restore():
    """Restoring a version repoints the item on its blob and records a new version."""
    user = factories.UserFactory()
    item, v1, _ = _make_item_with_versions(user)

    client = APIClient()
    client.force_login(user)
    response = client.post(f"/api/v1.0/items/{item.id!s}/versions/{v1.id!s}/restore/")

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.blob_id == v1.blob_id
    assert item.filename == "doc.txt"  # the item keeps its own filename
    assert item.versions.count() == 3  # the restore is recorded as a new version


def test_api_item_versions_restore_blocked_by_wopi_lock():
    """Restore is refused while a WOPI editing session holds the lock."""
    user = factories.UserFactory()
    item, v1, _ = _make_item_with_versions(user)
    LockService(item).lock("lock-value")

    client = APIClient()
    client.force_login(user)
    response = client.post(f"/api/v1.0/items/{item.id!s}/versions/{v1.id!s}/restore/")

    assert response.status_code == 409
    item.refresh_from_db()
    assert item.blob_id != v1.blob_id


def test_api_item_versions_destroy():
    """Deleting a non-current version detaches its blob reference; the blob becomes
    unreferenced and is left to the garbage collector."""
    user = factories.UserFactory()
    item, v1, _ = _make_item_with_versions(user)
    blob_v1 = v1.blob

    client = APIClient()
    client.force_login(user)
    response = client.delete(f"/api/v1.0/items/{item.id!s}/versions/{v1.id!s}/")

    assert response.status_code == 204
    assert not models.ItemVersion.objects.filter(pk=v1.id).exists()
    blob_v1.refresh_from_db()
    assert blob_v1.unreferenced_at is not None


def test_api_item_versions_destroy_current_forbidden():
    """The current version cannot be deleted."""
    user = factories.UserFactory()
    item, _, v2 = _make_item_with_versions(user)

    client = APIClient()
    client.force_login(user)
    response = client.delete(f"/api/v1.0/items/{item.id!s}/versions/{v2.id!s}/")

    assert response.status_code == 400
    assert models.ItemVersion.objects.filter(pk=v2.id).exists()
