"""Tests for the item versions API endpoints."""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from core import factories, models

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


def _make_versions(item, count=3):
    versions = []
    for n in range(1, count + 1):
        versions.append(
            models.ItemVersion.objects.create(
                item=item,
                filename=item.filename,
                mimetype=item.mimetype,
                size=item.size,
                version_number=n,
                created_by=item.creator,
            )
        )
    return versions


def test_versions_list_anonymous():
    """Anonymous users cannot list versions."""
    item = _file_item(factories.UserFactory())
    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/versions/")
    assert response.status_code == 401


def test_versions_list_requires_access():
    """Authenticated users without access cannot list versions."""
    user = factories.UserFactory()
    item = _file_item(factories.UserFactory())
    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/versions/")
    assert response.status_code == 403


def test_versions_list_ordering_by_version_number_desc():
    """Versions are listed newest first."""
    user = factories.UserFactory()
    item = _file_item(user)
    _make_versions(item, count=3)
    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/versions/")
    assert response.status_code == 200
    versions = response.json()
    assert [v["version_number"] for v in versions] == [3, 2, 1]
    assert "id" in versions[0]
    assert "item" in versions[0]
    assert "created_by" in versions[0]


def test_versions_list_reader_can_view():
    """Readers can list versions."""
    user = factories.UserFactory()
    item = _file_item(
        factories.UserFactory(),
        users=[(user, models.RoleChoices.READER)],
    )
    _make_versions(item)
    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/versions/")
    assert response.status_code == 200


def test_versions_download_redirects():
    """Download redirects to the media URL of the stored version."""
    user = factories.UserFactory()
    item = _file_item(user)
    version = _make_versions(item)[0]
    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/versions/{version.id!s}/download/")
    assert response.status_code == 302
    assert str(version.file_key) in response["Location"]


def test_versions_restore_owner():
    """An owner can restore a version."""
    user = factories.UserFactory()
    item = _file_item(user)
    version = _make_versions(item)[0]

    client = APIClient()
    client.force_login(user)
    with (
        mock.patch(
            "core.services.item_versions.default_storage.exists",
            return_value=True,
        ),
        mock.patch("core.services.item_versions._s3"),
    ):
        response = client.post(f"/api/v1.0/items/{item.id!s}/versions/{version.id!s}/restore/")
    assert response.status_code == 204


def test_versions_restore_reader_forbidden():
    """Readers cannot restore a version."""
    user = factories.UserFactory()
    item = _file_item(
        factories.UserFactory(),
        users=[(user, models.RoleChoices.READER)],
    )
    version = _make_versions(item)[0]
    client = APIClient()
    client.force_login(user)
    response = client.post(f"/api/v1.0/items/{item.id!s}/versions/{version.id!s}/restore/")
    assert response.status_code == 403


def test_versions_delete_owner():
    """An owner can delete a stored version."""
    user = factories.UserFactory()
    item = _file_item(user)
    version = _make_versions(item)[0]

    client = APIClient()
    client.force_login(user)
    with mock.patch("core.services.item_versions._s3"):
        response = client.delete(f"/api/v1.0/items/{item.id!s}/versions/{version.id!s}/")
    assert response.status_code == 204
    assert not item.versions.filter(pk=version.pk).exists()


def test_versions_delete_editor_forbidden():
    """Editors cannot delete a version (only owners/admins can destroy)."""
    user = factories.UserFactory()
    item = _file_item(
        factories.UserFactory(),
        users=[(user, models.RoleChoices.EDITOR)],
    )
    version = _make_versions(item)[0]
    client = APIClient()
    client.force_login(user)
    response = client.delete(f"/api/v1.0/items/{item.id!s}/versions/{version.id!s}/")
    assert response.status_code == 403


def test_versions_editor_can_restore():
    """Editors can restore a version (update ability)."""
    user = factories.UserFactory()
    item = _file_item(
        factories.UserFactory(),
        users=[(user, models.RoleChoices.EDITOR)],
    )
    version = _make_versions(item)[0]

    client = APIClient()
    client.force_login(user)
    with (
        mock.patch(
            "core.services.item_versions.default_storage.exists",
            return_value=True,
        ),
        mock.patch("core.services.item_versions._s3"),
    ):
        response = client.post(f"/api/v1.0/items/{item.id!s}/versions/{version.id!s}/restore/")
    assert response.status_code == 204


def test_versions_list_only_returns_item_versions():
    """Only versions of the targeted item are returned."""
    user = factories.UserFactory()
    item = _file_item(user)
    other = _file_item(user)
    _make_versions(item, count=2)
    _make_versions(other, count=4)
    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/versions/")
    assert response.status_code == 200
    assert len(response.json()) == 2
