"""Tests for replacing a file with a new version."""

from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.services.item_versions import replacement_cache_key

pytestmark = pytest.mark.django_db


def _file_item(user, **kwargs):
    defaults = {
        "type": models.ItemTypeChoices.FILE,
        "update_upload_state": models.ItemUploadStateChoices.READY,
        "filename": "content.txt",
        "mimetype": "text/plain",
        "size": 5,
        "users": [(user, models.RoleChoices.OWNER)],
    }
    defaults.update(kwargs)
    return factories.ItemFactory(**defaults)


def test_new_version_anonymous():
    """Anonymous users cannot replace a file."""
    item = _file_item(factories.UserFactory())
    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/new-version/",
        {"size": 12},
        format="json",
    )
    assert response.status_code == 401


def test_new_version_reader_forbidden():
    """Readers cannot replace a file."""
    user = factories.UserFactory()
    item = _file_item(
        factories.UserFactory(),
        users=[(user, models.RoleChoices.READER)],
    )
    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/new-version/",
        {"size": 12},
        format="json",
    )
    assert response.status_code == 403
    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert item.size == 5


def test_new_version_snapshots_and_returns_policy(django_capture_on_commit_callbacks):
    """Replacing a ready file snapshots it and returns an upload policy."""
    user = factories.UserFactory()
    item = _file_item(user)
    client = APIClient()
    client.force_login(user)

    with (
        mock.patch(
            "core.services.item_versions.default_storage.exists",
            return_value=True,
        ),
        mock.patch("core.services.item_versions._s3") as s3,
        mock.patch(
            "core.api.serializers.utils.generate_upload_policy",
            return_value="https://upload.example/policy",
        ),
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = client.post(
            f"/api/v1.0/items/{item.id!s}/new-version/",
            {"size": 12},
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["policy"] == "https://upload.example/policy"
    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.PENDING
    assert item.size == 12
    version = models.ItemVersion.objects.get(item=item)
    assert version.size == 5
    assert version.filename == "content.txt"
    s3.return_value.copy_object.assert_called_once()
    assert cache.get(replacement_cache_key(item.pk)) == str(version.pk)


def test_new_version_requires_size():
    """A replacement declares the size it will upload."""
    user = factories.UserFactory()
    item = _file_item(user)
    client = APIClient()
    client.force_login(user)
    response = client.post(f"/api/v1.0/items/{item.id!s}/new-version/", {}, format="json")
    assert response.status_code == 400


def test_new_version_rejects_oversized(settings):
    """A replacement cannot reserve more than the upload limit."""
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 10
    user = factories.UserFactory()
    item = _file_item(user)
    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/new-version/",
        {"size": 11},
        format="json",
    )
    assert response.status_code == 400
    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.READY


def test_new_version_rejects_pending_file():
    """A file that is still uploading cannot be snapshotted."""
    user = factories.UserFactory()
    item = _file_item(user, update_upload_state=models.ItemUploadStateChoices.PENDING)
    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/new-version/",
        {"size": 12},
        format="json",
    )
    assert response.status_code == 400


def test_cancel_new_version_restores_snapshot(django_capture_on_commit_callbacks):
    """Aborting a replacement puts the snapshotted content back."""
    user = factories.UserFactory()
    item = _file_item(user)
    client = APIClient()
    client.force_login(user)
    storage = mock.patch("core.services.item_versions.default_storage.exists", return_value=True)
    s3 = mock.patch("core.services.item_versions._s3")
    policy = mock.patch(
        "core.api.serializers.utils.generate_upload_policy",
        return_value="https://upload.example/policy",
    )

    with storage, s3, policy, django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            f"/api/v1.0/items/{item.id!s}/new-version/",
            {"size": 12},
            format="json",
        )
    assert response.status_code == 200

    with storage, s3:
        cancel = client.post(f"/api/v1.0/items/{item.id!s}/cancel-new-version/")

    assert cancel.status_code == 204
    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert item.size == 5
    assert item.mimetype == "text/plain"
    assert not models.ItemVersion.objects.filter(item=item).exists()
    assert cache.get(replacement_cache_key(item.pk)) is None


def test_upload_ended_restores_replacement_when_mimetype_rejected(settings):
    """A rejected replacement keeps the file and restores the snapshot."""
    settings.RESTRICT_UPLOAD_FILE_TYPE = "allowlist"
    settings.FILE_MIMETYPE_ALLOWED = ["application/pdf"]
    user = factories.UserFactory()
    item = _file_item(user, size=8)
    item.upload_state = models.ItemUploadStateChoices.PENDING
    item.save(update_fields=["upload_state", "updated_at"])
    version = models.ItemVersion.objects.create(
        item=item,
        filename=item.filename,
        mimetype="application/pdf",
        size=4,
        version_number=1,
        created_by=user,
    )
    cache.set(replacement_cache_key(item.pk), str(version.pk), timeout=60)
    default_storage.save(item.file_key, BytesIO(b"my prose"))

    client = APIClient()
    client.force_login(user)
    with mock.patch("core.services.item_versions._s3"):
        response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 400
    item.refresh_from_db()
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert item.size == 4
    assert item.mimetype == "application/pdf"
    assert models.Item.objects.filter(id=item.id).exists()
    assert not models.ItemVersion.objects.filter(pk=version.pk).exists()
