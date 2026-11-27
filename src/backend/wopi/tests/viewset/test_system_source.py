"""Test the endpoint serving file contents to WOPI clients running background jobs."""

from io import BytesIO

from django.core import signing
from django.core.files.storage import default_storage

import pytest
from freezegun import freeze_time
from rest_framework.test import APIClient

from core import factories, models
from wopi.conversion.source_url import SOURCE_TOKEN_SALT

pytestmark = pytest.mark.django_db


def _file(upload_state=models.ItemUploadStateChoices.READY):
    """Create a restricted file whose content is in the object storage."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="report.docx",
        update_upload_state=upload_state,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
    default_storage.save(item.file_key, BytesIO(b"my prose"))
    return item


def _token(item_id):
    return signing.dumps(str(item_id), salt=SOURCE_TOKEN_SALT)


def test_system_source_streams_the_file():
    """A valid token gives access to the content without any user."""
    item = _file()

    response = APIClient().get(f"/api/v1.0/wopi/sources/{item.id}/?token={_token(item.id)}")

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"my prose"


def test_system_source_works_without_creator_access():
    """The creator losing access to the file does not matter."""
    item = _file()
    models.ItemAccess.objects.filter(item=item).delete()
    item.creator = factories.UserFactory()
    item.save()

    response = APIClient().get(f"/api/v1.0/wopi/sources/{item.id}/?token={_token(item.id)}")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "token",
    [None, "", "forged", signing.dumps("x")],
    ids=["missing", "empty", "forged", "other-salt"],
)
def test_system_source_rejects_invalid_tokens(token):
    """Missing, forged or differently salted tokens are rejected."""
    item = _file()
    query = "" if token is None else f"?token={token}"

    response = APIClient().get(f"/api/v1.0/wopi/sources/{item.id}/{query}")

    assert response.status_code == 403


def test_system_source_rejects_token_of_another_item():
    """A token only gives access to the item it was signed for."""
    item = _file()
    other = _file()

    response = APIClient().get(f"/api/v1.0/wopi/sources/{item.id}/?token={_token(other.id)}")

    assert response.status_code == 403


def test_system_source_rejects_expired_token(settings):
    """Tokens expire after WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT."""
    settings.WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT = 60
    item = _file()
    with freeze_time("2026-10-03 12:00:00"):
        token = _token(item.id)

    with freeze_time("2026-10-03 12:01:01"):
        response = APIClient().get(f"/api/v1.0/wopi/sources/{item.id}/?token={token}")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "upload_state",
    [models.ItemUploadStateChoices.ANALYZING, models.ItemUploadStateChoices.SUSPICIOUS],
)
def test_system_source_only_serves_ready_files(upload_state):
    """Files that are not ready are not served, even with a valid token."""
    item = _file(upload_state)

    response = APIClient().get(f"/api/v1.0/wopi/sources/{item.id}/?token={_token(item.id)}")

    assert response.status_code == 404
