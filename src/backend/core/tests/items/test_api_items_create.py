"""
Tests for items API endpoint in drive's core app: create
"""

from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from django.conf import settings as django_settings
from django.utils import timezone

import pytest
from freezegun import freeze_time
from rest_framework.test import APIClient

from core import factories
from core.models import Item, ItemTypeChoices

pytestmark = pytest.mark.django_db


def test_api_items_create_anonymous():
    """Anonymous users should not be allowed to create items."""
    response = APIClient().post(
        "/api/v1.0/items/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
    )

    assert response.status_code == 401
    assert not Item.objects.exists()


def test_api_items_create_authenticated_success():
    """
    Authenticated users should be able to create items and should automatically be declared
    as the owner of the newly created item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )
    assert response.status_code == 201
    item = Item.objects.get()
    assert item.title == "my item"
    assert item.link_reach == "restricted"
    assert item.accesses.filter(role="owner", user=user).exists()
    assert item.type == ItemTypeChoices.FOLDER


@pytest.mark.parametrize("message", [None, "Hello World"])
@mock.patch("core.api.viewsets.get_entitlements_backend")
def test_api_items_create_entitlements_backend_returns_falsy(
    mock_get_entitlements_backend, message
):
    """
    Test that the API returns a 403 when the entitlements backend returns a falsy result.
    """
    mock_entitlement_backend = mock.Mock()
    return_value = {"result": False}
    if message:
        return_value["message"] = message
    mock_entitlement_backend.can_upload.return_value = return_value
    mock_get_entitlements_backend.return_value = mock_entitlement_backend

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
        format="json",
    )

    assert response.status_code == 403
    assert not Item.objects.exists()
    assert response.json() == {
        "type": "client_error",
        "errors": [
            {
                "code": "permission_denied",
                "detail": message or "You do not have permission to upload files.",
                "attr": None,
            }
        ],
    }


def test_api_items_create_file_authenticated_no_filename():
    """
    Creating a file item without providing a filename should fail.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "filename",
                "code": "item_create_file_filename_required",
                "detail": "This field is required for files.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_create_file_authenticated_success():
    """
    Authenticated users should be able to create a file item and must provide a filename.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    now = timezone.now()
    with freeze_time(now):
        response = client.post(
            "/api/v1.0/items/",
            {
                "type": ItemTypeChoices.FILE,
                "filename": "file.txt",
            },
            format="json",
        )
    assert response.status_code == 201
    item = Item.objects.get()
    assert item.title == "file.txt"
    assert item.link_reach == "restricted"
    assert item.accesses.filter(role="owner", user=user).exists()
    assert item.type == ItemTypeChoices.FILE
    assert item.filename == "file.txt"

    assert response.json().get("policy") is not None

    policy = response.json()["policy"]
    policy_parsed = urlparse(policy)

    assert policy_parsed.scheme == "http"
    assert policy_parsed.netloc == "localhost:9000"
    assert policy_parsed.path == f"/drive-media-storage/item/{item.id!s}/file.txt"

    query_params = parse_qs(policy_parsed.query)

    assert query_params.pop("X-Amz-Algorithm") == ["AWS4-HMAC-SHA256"]
    assert query_params.pop("X-Amz-Credential") == [
        f"drive/{now.strftime('%Y%m%d')}/{django_settings.AWS_S3_REGION_NAME}/s3/aws4_request"
    ]
    assert query_params.pop("X-Amz-Date") == [now.strftime("%Y%m%dT%H%M%SZ")]
    assert query_params.pop("X-Amz-Expires") == ["60"]
    assert query_params.pop("X-Amz-SignedHeaders") == ["host;x-amz-acl"]
    assert query_params.pop("X-Amz-Signature") is not None

    assert len(query_params) == 0


def test_api_items_create_file_authenticated_extension_not_allowed():
    """
    Creating a file item with an extension not allowed should fail.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file.notallowed",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "filename",
                "code": "item_create_file_extension_not_allowed",
                "detail": "This file extension is not allowed.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_create_file_authenticated_extension_case_insensitive():
    """
    Creating a file item with an extension, no matter the case used, should be allowed.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file.JPG",
        },
        format="json",
    )
    assert response.status_code == 201
    item = Item.objects.get()
    assert item.title == "file.JPG"


def test_api_items_create_file_authenticated_not_checking_extension(settings):
    """
    Creating a file item with an extension not allowed should fail.
    """
    settings.RESTRICT_UPLOAD_FILE_TYPE = False
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file.notallowed",
        },
        format="json",
    )
    assert response.status_code == 201
    item = Item.objects.get()
    assert item.title == "file.notallowed"


def test_api_items_create_file_authenticated_no_extension_but_checking_it_should_fail(
    settings,
):
    """
    Creating a file without an extension but checking the extension should fail.
    """
    settings.RESTRICT_UPLOAD_FILE_TYPE = True
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "filename",
                "code": "item_create_file_extension_not_allowed",
                "detail": "This file extension is not allowed.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_create_file_authenticated_hidden_file_but_checking_extension_should_fail(
    settings,
):
    """
    Creating a hidden file (starting with a dot) but checking the extension should fail.
    """
    settings.RESTRICT_UPLOAD_FILE_TYPE = True
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": ".file",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "filename",
                "code": "item_create_file_extension_not_allowed",
                "detail": "This file extension is not allowed.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_create_authenticated_title_null():
    """It should not be possible to create several items with a null title."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/", {"type": ItemTypeChoices.FOLDER}, format="json"
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "title",
                "code": "item_create_folder_title_required",
                "detail": "This field is required for folders.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_create_force_id_success():
    """It should be possible to force the item ID when creating a   item."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    forced_id = uuid4()

    response = client.post(
        "/api/v1.0/items/",
        {
            "id": str(forced_id),
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )

    assert response.status_code == 201
    items = Item.objects.all()
    assert len(items) == 1
    assert items[0].id == forced_id


def test_api_items_create_force_id_existing():
    """
    It should not be possible to use the ID of an existing item when forcing ID on creation.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()

    response = client.post(
        "/api/v1.0/items/",
        {
            "id": str(item.id),
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "id",
                "code": "item_create_existing_id",
                "detail": "An item with this ID already exists. You cannot override it.",
            },
        ],
        "type": "validation_error",
    }


@pytest.mark.django_db(transaction=True)
def test_api_items_create_item_race_condition():
    """
    It should be possible to create several items at the same time
    without causing any race conditions or data integrity issues.
    """

    def create_item(title):
        user = factories.UserFactory()
        client = APIClient()
        client.force_login(user)
        return client.post(
            "/api/v1.0/items/",
            {
                "title": title,
                "type": ItemTypeChoices.FOLDER,
            },
            format="json",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(create_item, "my item 1")
        future2 = executor.submit(create_item, "my item 2")

        response1 = future1.result()
        response2 = future2.result()

        assert response1.status_code == 201
        assert response2.status_code == 201
