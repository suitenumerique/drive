"""
Test file uploads API endpoint for users in drive's core app.
"""

import uuid
from io import BytesIO
from urllib.parse import quote, urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

import pytest
import requests
from rest_framework.test import APIClient

from core import factories, models
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


def test_api_items_media_auth_anonymous_public():
    """Anonymous users should be able to retrieve attachments linked to a public item"""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )

    filename = f"{uuid.uuid4()!s}.jpg"
    key = f"item/{item.pk!s}/{filename:s}"

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    original_url = f"http://localhost/media/{key:s}"
    response = APIClient().get(
        "/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url
    )

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert (
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature="
        in authorization
    )
    assert response["X-Amz-Date"] == timezone.now().strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL:s}/drive-media-storage/{key:s}"
    response = requests.get(
        file_url,
        headers={
            "authorization": authorization,
            "x-amz-date": response["x-amz-date"],
            "x-amz-content-sha256": response["x-amz-content-sha256"],
            "Host": f"{s3_url.hostname:s}:{s3_url.port:d}",
        },
        timeout=1,
    )
    assert response.content.decode("utf-8") == "my prose"


@pytest.mark.parametrize("reach", ["authenticated", "restricted"])
def test_api_items_media_auth_anonymous_authenticated_or_restricted(reach):
    """
    Anonymous users should not be allowed to retrieve attachments linked to an item
    with link reach set to authenticated or restricted.
    """
    item = factories.ItemFactory(link_reach=reach)

    filename = f"{uuid.uuid4()!s}.jpg"
    media_url = f"http://localhost/media/item/{item.pk!s}/{filename:s}"

    response = APIClient().get(
        "/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=media_url
    )

    assert response.status_code == 403
    assert "Authorization" not in response


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_media_auth_authenticated_public_or_authenticated(reach):
    """
    Authenticated users who are not related to an item should be able to retrieve
    attachments related to an item with public or authenticated link reach.
    """
    item = factories.ItemFactory(
        link_reach=reach,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    filename = f"{uuid.uuid4()!s}.jpg"
    key = f"item/{item.pk!s}/{filename:s}"

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    original_url = f"http://localhost/media/{key:s}"
    response = client.get(
        "/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url
    )

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert (
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature="
        in authorization
    )
    assert response["X-Amz-Date"] == timezone.now().strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL:s}/drive-media-storage/{key:s}"
    response = requests.get(
        file_url,
        headers={
            "authorization": authorization,
            "x-amz-date": response["x-amz-date"],
            "x-amz-content-sha256": response["x-amz-content-sha256"],
            "Host": f"{s3_url.hostname:s}:{s3_url.port:d}",
        },
        timeout=1,
    )
    assert response.content.decode("utf-8") == "my prose"


def test_api_items_media_auth_authenticated_restricted():
    """
    Authenticated users who are not related to an item should not be allowed to
    retrieve attachments linked to an item that is restricted.
    """
    item = factories.ItemFactory(
        link_reach="restricted",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    filename = f"{uuid.uuid4()!s}.jpg"
    media_url = f"http://localhost/media/item/{item.pk!s}/{filename:s}"

    response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=media_url)

    assert response.status_code == 403
    assert "Authorization" not in response


@pytest.mark.parametrize("via", VIA)
def test_api_items_media_auth_related(via, mock_user_teams):
    """
    Users who have a specific access to an item, whatever the role, should be able to
    retrieve related attachments.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite")

    filename = f"{uuid.uuid4()!s}.jpg"
    key = f"item/{item.pk!s}/{filename:s}"

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    original_url = f"http://localhost/media/{key:s}"
    response = client.get(
        "/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url
    )

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert (
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature="
        in authorization
    )
    assert response["X-Amz-Date"] == timezone.now().strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL:s}/drive-media-storage/{key:s}"
    response = requests.get(
        file_url,
        headers={
            "authorization": authorization,
            "x-amz-date": response["x-amz-date"],
            "x-amz-content-sha256": response["x-amz-content-sha256"],
            "Host": f"{s3_url.hostname:s}:{s3_url.port:d}",
        },
        timeout=1,
    )
    assert response.content.decode("utf-8") == "my prose"


def test_api_items_media_auth_related_filename_with_espaces():
    """
    Users who have a specific access to an item, whatever the role, should be able to
    retrieve related attachments.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.UPLOADED,
    )

    factories.UserItemAccessFactory(item=item, user=user)

    filename = "image with & spaces.txt"
    key = f"item/{item.pk!s}/{filename:s}"

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    original_url = quote(f"http://localhost/media/{key:s}")
    response = client.get(
        "/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url
    )

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert (
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature="
        in authorization
    )
    assert response["X-Amz-Date"] == timezone.now().strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL:s}/drive-media-storage/{key:s}"
    response = requests.get(
        file_url,
        headers={
            "authorization": authorization,
            "x-amz-date": response["x-amz-date"],
            "x-amz-content-sha256": response["x-amz-content-sha256"],
            "Host": f"{s3_url.hostname:s}:{s3_url.port:d}",
        },
        timeout=1,
    )
    assert response.content.decode("utf-8") == "my prose"


def test_api_items_media_auth_item_not_a_file():
    """
    Users who have a specific access to an item, whatever the role, should not be able to
    retrieve related attachments if the item is not a file.
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    factories.UserItemAccessFactory(item=item, user=user)

    filename = "foo.txt"
    key = f"item/{item.pk!s}/{filename:s}"

    original_url = quote(f"http://localhost/media/{key:s}")
    response = client.get(
        "/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url
    )

    assert response.status_code == 403


def test_api_items_media_auth_item_not_uploaded():
    """
    Users who have a specific access to an item, whatever the role, should not be able to
    retrieve related attachments if the item is not uploaded.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE)
    factories.UserItemAccessFactory(item=item, user=user)

    filename = "foo.txt"
    key = f"item/{item.pk!s}/{filename:s}"

    original_url = quote(f"http://localhost/media/{key:s}")
    response = client.get(
        "/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url
    )

    assert response.status_code == 403
