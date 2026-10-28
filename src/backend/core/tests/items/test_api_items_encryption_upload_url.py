"""Tests for the upload URLs of encrypted content on API endpoint."""

from urllib.parse import parse_qs, urlparse

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def request_upload_url(item, user, data):
    """Ask for an upload URL of encrypted content for `item` as `user`."""
    client = APIClient()
    client.force_login(user)
    return client.post(f"/api/v1.0/items/{item.id!s}/encryption-upload-url/", data, format="json")


def test_api_items_encryption_upload_url_signs_the_size():
    """The URL signs the declared length, as any upload: it is no write grant of any size."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, models.RoleChoices.OWNER)]
    )

    response = request_upload_url(item, user, {"filename": "staged.bin", "size": 42})

    assert response.status_code == 200
    assert response.json()["filename"] == "staged.bin"
    query = parse_qs(urlparse(response.json()["upload_url"]).query)
    assert "content-length" in query["X-Amz-SignedHeaders"][0].split(";")
    assert urlparse(response.json()["upload_url"]).path.endswith(f"{item.key_base}/staged.bin")


@pytest.mark.parametrize("size", [None, -1, "42", True])
def test_api_items_encryption_upload_url_requires_a_size(size):
    """Without a valid length, no URL is given."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, models.RoleChoices.OWNER)]
    )
    data = {"filename": "staged.bin"}
    if size is not None:
        data["size"] = size

    response = request_upload_url(item, user, data)

    assert response.status_code == 400
    assert response.json()["errors"][0]["attr"] == "size"


def test_api_items_encryption_upload_url_size_above_the_maximum(settings):
    """A length above the maximum upload size is refused."""
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 100
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, models.RoleChoices.OWNER)]
    )

    response = request_upload_url(item, user, {"filename": "staged.bin", "size": 101})

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "file_size_exceeded"


def test_api_items_encryption_upload_url_save_of_a_file_no_longer_encrypted():
    """Saving over the current content is refused once the file is plaintext again."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, models.RoleChoices.OWNER)]
    )

    response = request_upload_url(item, user, {"size": 42})

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_not_encrypted"


def test_api_items_encryption_upload_url_save_of_an_encrypted_file():
    """Saving over the current content of an encrypted file gets a URL for its key."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        users=[(user, models.RoleChoices.EDITOR)],
        is_encrypted=True,
    )

    response = request_upload_url(item, user, {"size": 42})

    assert response.status_code == 200
    assert response.json()["filename"] == item.filename


def test_api_items_encryption_upload_url_reader_forbidden():
    """A reader cannot upload content."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, models.RoleChoices.READER)]
    )

    response = request_upload_url(item, user, {"filename": "staged.bin", "size": 42})

    assert response.status_code == 403
