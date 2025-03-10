"""Test for items API endpoint managing wopi init request."""

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


@pytest.fixture
def timestamp_now():
    """Timestamp now in milliseconds."""
    return int(round(timezone.now().timestamp())) * 1000


@pytest.fixture
def valid_mimetype():
    """Valid mimetype for testing."""
    return "application/vnd.oasis.opendocument.text"


@pytest.fixture
def valid_wopi_launch_url():
    """Valid WOPI launch URL for testing."""
    return "https://vendorA.com/launch_url"


@pytest.fixture(autouse=True)
def configure_wopi_settings(settings, valid_mimetype, valid_wopi_launch_url):
    settings.WOPI_CLIENTS = ["vendorA"]
    settings.WOPI_CLIENTS_CONFIGURATION = {
        "vendorA": {
            "launch_url": valid_wopi_launch_url,
            "mimetypes": [valid_mimetype],
        }
    }


def test_api_items_wopi_not_existing_item():
    """
    Anonymous user cannot generate wopi access token for non-existing item.
    """

    client = APIClient()
    response = client.get("/api/v1.0/items/00000000-0000-0000-0000-000000000000/wopi/")

    assert response.status_code == 404


def test_api_items_wopi_anonymous_user_item_public(
    timestamp_now, valid_mimetype, valid_wopi_launch_url
):
    """
    Anonymous user can generate wopi access token for public item.
    """

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.PUBLIC,
        type=models.ItemTypeChoices.FILE,
        mimetype=valid_mimetype,
    )
    item.upload_state = models.ItemUploadStateChoices.UPLOADED
    item.save()

    client = APIClient()
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None
    assert data["access_token_ttl"] > timestamp_now
    assert data["launch_url"] == valid_wopi_launch_url


@pytest.mark.parametrize(
    "link_reach",
    [models.LinkReachChoices.AUTHENTICATED, models.LinkReachChoices.RESTRICTED],
)
def test_api_items_wopi_anonymous_user_item_not_public(link_reach):
    """Anymous user can not access not public item."""
    item = factories.ItemFactory(link_reach=link_reach)

    client = APIClient()
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 401


def test_api_items_wopi_anonymous_user_not_item_file():
    """Anymous user can not access item that is not a file."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, link_reach=models.LinkReachChoices.PUBLIC
    )

    client = APIClient()
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 400
    assert response.json() == {"detail": "This item does not suport WOPI integration."}


def test_api_items_wopi_anonymous_item_file_mimetype_not_supported():
    """Anymous user can not access item file with mimetype not supported."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        mimetype="image/png",
        link_reach=models.LinkReachChoices.PUBLIC,
    )
    item.upload_state = models.ItemUploadStateChoices.UPLOADED
    item.save()

    client = APIClient()
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 400
    assert response.json() == {"detail": "This item does not suport WOPI integration."}


def test_api_items_wopi_anonymous_user_item_not_uploaded():
    """Anymous user can not access item file that is not uploaded."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        mimetype="image/png",
        link_reach=models.LinkReachChoices.PUBLIC,
    )

    client = APIClient()
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 400
    assert response.json() == {"detail": "This item does not suport WOPI integration."}


def test_api_items_wopi_authenticated_user_item_not_accessible():
    """Authenticated user can not access item that is not accessible."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 403


def test_api_items_wopi_authenticated_can_access_retricted_item(
    timestamp_now, valid_mimetype, valid_wopi_launch_url
):
    """Authenticated user can access item that is accessible."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FILE,
        mimetype=valid_mimetype,
    )
    item.upload_state = models.ItemUploadStateChoices.UPLOADED
    item.save()
    factories.UserItemAccessFactory(user=user, item=item)

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None
    assert data["access_token_ttl"] > timestamp_now
    assert data["launch_url"] == valid_wopi_launch_url


def test_api_items_wopi_authenticated_user_item_not_file():
    """Authenticated user can not access item that is not a file."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(user=user, item=item)

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 400
    assert response.json() == {"detail": "This item does not suport WOPI integration."}


def test_api_items_wopi_authenticated_user_item_mimetype_not_supported():
    """Authenticated user can not access item that mimetype is not supported."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FILE,
        mimetype="image/png",
    )
    item.upload_state = models.ItemUploadStateChoices.UPLOADED
    item.save()
    factories.UserItemAccessFactory(user=user, item=item)

    client = APIClient()
    client.force_login(user)
    response = client.get(f"/api/v1.0/items/{item.id!s}/wopi/")

    assert response.status_code == 400
    assert response.json() == {"detail": "This item does not suport WOPI integration."}
