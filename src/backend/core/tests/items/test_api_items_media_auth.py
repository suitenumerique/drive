"""
Test file uploads API endpoint for users in drive's core app.
"""

import uuid
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import quote, urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

import pytest
import requests
from freezegun import freeze_time
from rest_framework.test import APIClient

from core import factories, models
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


def test_api_items_media_auth_anonymous_public():
    """Anonymous users should be able to retrieve attachments linked to a public item"""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )
    original_url = f"http://localhost/media/{item.file_key:s}"
    now = timezone.now()
    with freeze_time(now):
        response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in authorization
    assert response["X-Amz-Date"] == now.strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL:s}/drive-media-storage/{item.file_key:s}"
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

    response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=media_url)

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
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )

    original_url = f"http://localhost/media/{item.file_key:s}"
    now = timezone.now()
    with freeze_time(now):
        response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in authorization
    assert response["X-Amz-Date"] == now.strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL:s}/drive-media-storage/{item.file_key:s}"
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
        update_upload_state=models.ItemUploadStateChoices.READY,
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
@pytest.mark.parametrize(
    "upload_state",
    [
        models.ItemUploadStateChoices.READY,
        models.ItemUploadStateChoices.ANALYZING,
        models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE,
    ],
)
def test_api_items_media_auth_related(via, mock_user_teams, upload_state):
    """
    Users who have a specific access to an item, whatever the role, should be able to
    retrieve related attachments if not pending.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=upload_state,
    )
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite")

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )

    original_url = f"http://localhost/media/{item.file_key:s}"
    now = timezone.now()
    with freeze_time(now):
        response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in authorization
    assert response["X-Amz-Date"] == now.strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL:s}/drive-media-storage/{item.file_key:s}"
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


def test_api_items_media_auth_related_filename_with_spaces():
    """
    Users who have a specific access to an item, whatever the role, should be able to
    retrieve related attachments.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    factories.UserItemAccessFactory(item=item, user=user)

    filename = "image with & spaces.txt"
    key = f"item/{item.pk!s}/{filename:s}"

    default_storage.save(key, BytesIO(b"my prose"))

    original_url = quote(f"http://localhost/media/{key:s}")
    now = timezone.now()
    with freeze_time(now):
        response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in authorization
    assert response["X-Amz-Date"] == now.strftime("%Y%m%dT%H%M%SZ")

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
    response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 403


def test_api_items_media_auth_item_pending():
    """
    Users who have a specific access to an item, whatever the role, should not be able to
    retrieve related attachments if the item is not ready.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        upload_state=models.ItemUploadStateChoices.PENDING,
    )
    factories.UserItemAccessFactory(item=item, user=user)

    filename = "foo.txt"
    key = f"item/{item.pk!s}/{filename:s}"

    original_url = quote(f"http://localhost/media/{key:s}")
    response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 403


def test_api_items_media_auth_suspicious_item_non_creator():
    """
    Users who have a specific access to an item, whatever the role, should not be able to
    retrieve related attachments if the item is suspicious and they are not the creator.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[(user, models.RoleChoices.OWNER)],
    )

    filename = "foo.txt"
    key = f"item/{item.pk!s}/{filename:s}"

    original_url = quote(f"http://localhost/media/{key:s}")
    response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 403


def test_api_items_media_auth_suspicious_item_creator():
    """
    Users who have a specific access to an item, whatever the role, should be able to
    retrieve related attachments if the item is suspicious and they are the creator.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        creator=user,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[(user, models.RoleChoices.OWNER)],
    )

    filename = "foo.txt"
    key = f"item/{item.pk!s}/{filename:s}"

    original_url = quote(f"http://localhost/media/{key:s}")
    now = timezone.now()
    with freeze_time(now):
        response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in authorization
    assert response["X-Amz-Date"] == now.strftime("%Y%m%dT%H%M%SZ")


def test_api_items_media_auth_filename_with_hash():
    """Files with '#' in their filename should not cause a SignatureDoesNotMatch."""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        filename="Spécial #4.pdf",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )
    original_url = f"http://localhost/media/{quote(item.file_key)}"
    now = timezone.now()
    with freeze_time(now):
        response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200

    authorization = response["Authorization"]
    assert "AWS4-HMAC-SHA256 Credential=" in authorization
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in authorization
    assert response["X-Amz-Date"] == now.strftime("%Y%m%dT%H%M%SZ")

    s3_url = urlparse(settings.AWS_S3_ENDPOINT_URL)
    file_url = f"{settings.AWS_S3_ENDPOINT_URL}/drive-media-storage/{quote(item.file_key)}"

    response = requests.get(
        file_url,
        headers={
            "authorization": authorization,
            "x-amz-date": response["x-amz-date"],
            "x-amz-content-sha256": response["x-amz-content-sha256"],
            "Host": f"{s3_url.hostname}:{s3_url.port}",
        },
        timeout=1,
    )
    assert response.content.decode("utf-8") == "my prose"


def test_api_items_media_auth_link_password_locked():
    """Attachments of a password protected item require the link to be unlocked."""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    item.set_link_password("s3cret")
    item.save()
    original_url = f"http://localhost/media/{item.file_key:s}"

    client = APIClient()
    response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)
    assert response.status_code == 403

    session = client.session
    session["unlocked_link_items"] = [item.link_unlock_key]
    session.save()

    response = client.get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "mimetype,filename",
    [("image/png", "image.png"), ("application/pdf", "document.pdf")],
)
def test_api_items_media_auth_security_headers_on_download(mimetype, filename):
    """Media downloads should be served as attachments."""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        filename=filename,
        mimetype=mimetype,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    original_url = f"http://localhost/media/{item.file_key:s}"
    response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200
    assert response["Content-Disposition"] == "attachment"


@pytest.mark.parametrize(
    "mimetype,filename",
    [("image/png", "image.png"), ("application/pdf", "document.pdf")],
)
def test_api_items_media_auth_security_headers_on_inline_preview(mimetype, filename):
    """PNG and PDF previews should stay inline."""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        filename=filename,
        mimetype=mimetype,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    original_url = f"http://localhost/media/preview/{item.file_key:s}"
    response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200
    assert "Content-Disposition" not in response


def test_api_items_media_auth_security_headers_on_active_content_preview():
    """Force SVG previews to download when opened directly."""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        filename="payload.svg",
        mimetype="image/svg+xml",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    original_url = f"http://localhost/media/preview/{item.file_key:s}"
    response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 200
    assert response["Content-Disposition"] == "attachment"


@pytest.mark.parametrize(
    "key_suffix,status_code",
    [
        ("thumbnail/1791028800000.png", 200),
        # A previous render, its object was deleted when the current one was stored.
        ("thumbnail/1791025200000.png", 403),
        ("report.docx", 403),
    ],
)
def test_api_items_media_auth_preview_thumbnail(key_suffix, status_code):
    """The current thumbnail of a non-previewable file can be previewed, not the file itself."""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        filename="report.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        update_upload_state=models.ItemUploadStateChoices.READY,
        thumbnail_updated_at=datetime(2026, 10, 3, 12, tzinfo=UTC),
    )

    original_url = f"http://localhost/media/preview/item/{item.pk!s}/{key_suffix:s}"
    response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == status_code


def test_api_items_media_auth_preview_thumbnail_none():
    """A file without a thumbnail has no thumbnail key to preview."""
    item = factories.ItemFactory(
        link_reach="public",
        type=models.ItemTypeChoices.FILE,
        filename="report.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    original_url = f"http://localhost/media/preview/item/{item.pk!s}/thumbnail/1791028800000.png"
    response = APIClient().get("/api/v1.0/items/media-auth/", HTTP_X_ORIGINAL_URL=original_url)

    assert response.status_code == 403
