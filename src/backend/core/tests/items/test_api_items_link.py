"""
Tests for link items: a titled pointer to an external web URL.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db

LINK_URL = "https://example.com/some/page?query=1"


def _owned_folder(user):
    """Return a folder owned by the user."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.OWNER)
    return folder


def _error(response):
    """Return the (attr, code) of the single validation error of a response."""
    assert response.status_code == 400
    errors = response.json()["errors"]
    assert len(errors) == 1
    return errors[0]["attr"], errors[0]["code"]


def test_api_items_link_create_root():
    """A link can be created at the root, it has no content to upload."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {"type": "link", "title": "Example", "link_url": LINK_URL},
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["type"] == "link"
    assert payload["title"] == "Example"
    assert payload["link_url"] == LINK_URL
    assert payload["policy"] is None
    assert payload["upload_state"] is None
    assert payload["url"] is None

    item = models.Item.objects.get(id=payload["id"])
    assert item.link_url == LINK_URL
    assert item.upload_state is None
    assert item.filename is None
    assert item.size is None
    assert item.source == models.ItemSourceChoices.CREATE
    assert item.accesses.filter(user=user, role=models.RoleChoices.OWNER).exists()


def test_api_items_link_create_child():
    """A link can be created in a folder and inherits its accesses."""
    user = factories.UserFactory()
    reader = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    folder = _owned_folder(user)
    factories.UserItemAccessFactory(item=folder, user=reader, role=models.RoleChoices.READER)

    response = client.post(
        f"/api/v1.0/items/{folder.id!s}/children/",
        {"type": "link", "title": "Example", "link_url": LINK_URL},
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["link_url"] == LINK_URL
    assert payload["policy"] is None
    assert payload["upload_state"] is None
    link = models.Item.objects.get(id=payload["id"])
    assert str(link.path).startswith(str(folder.path))
    assert link.source == models.ItemSourceChoices.CREATE

    # A reader of the folder reads the link and its URL, in the listing and on retrieve
    reader_client = APIClient()
    reader_client.force_login(reader)
    response = reader_client.get(f"/api/v1.0/items/{folder.id!s}/children/")
    assert response.status_code == 200
    assert [(r["id"], r["link_url"]) for r in response.json()["results"]] == [
        (str(link.id), LINK_URL)
    ]
    response = reader_client.get(f"/api/v1.0/items/{link.id!s}/")
    assert response.status_code == 200
    assert response.json()["link_url"] == LINK_URL


def test_api_items_link_url_is_null_on_other_types():
    """Folders and files expose a null link_url."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    folder = _owned_folder(user)

    response = client.get(f"/api/v1.0/items/{folder.id!s}/")

    assert response.status_code == 200
    assert response.json()["link_url"] is None


@pytest.mark.parametrize(
    "link_url",
    [
        "javascript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "//example.com/page",
        "not a url",
        f"https://example.com/{'a' * 2048}",
    ],
)
def test_api_items_link_create_invalid_url(link_url):
    """Only http and https URLs up to 2048 characters are accepted."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {"type": "link", "title": "Example", "link_url": link_url},
        format="json",
    )

    assert response.status_code == 400
    assert {error["attr"] for error in response.json()["errors"]} == {"link_url"}
    assert not models.Item.objects.exists()


@pytest.mark.parametrize("payload", [{}, {"link_url": None}, {"link_url": ""}])
def test_api_items_link_create_url_required(payload):
    """A link cannot be created without a URL."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/", {"type": "link", "title": "Example", **payload}, format="json"
    )

    assert _error(response)[0] == "link_url"
    assert not models.Item.objects.exists()


def test_api_items_link_create_title_required():
    """A link cannot be created without a title."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post("/api/v1.0/items/", {"type": "link", "link_url": LINK_URL})

    assert _error(response) == ("title", "item_create_link_title_required")


@pytest.mark.parametrize(
    "extra",
    [{"filename": "file.txt"}, {"extension": "odt"}, {"size": 12}],
)
def test_api_items_link_create_file_attributes_forbidden(extra):
    """A link has no content: file attributes are rejected."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {"type": "link", "title": "Example", "link_url": LINK_URL, **extra},
        format="json",
    )

    assert _error(response)[0] == next(iter(extra))
    assert not models.Item.objects.exists()


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "folder", "title": "Folder"},
        {"type": "file", "filename": "file.txt", "size": 12},
    ],
)
def test_api_items_link_url_forbidden_on_other_types(payload):
    """Only links accept a link_url on creation."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post("/api/v1.0/items/", {**payload, "link_url": LINK_URL}, format="json")

    assert _error(response) == ("link_url", "item_create_link_url_only_allowed_for_links")
    assert not models.Item.objects.exists()


def test_api_items_link_cannot_have_children():
    """Nothing can be created under a link."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    link = factories.ItemFactory(parent=_owned_folder(user), type=models.ItemTypeChoices.LINK)

    response = client.post(
        f"/api/v1.0/items/{link.id!s}/children/",
        {"type": "folder", "title": "Folder"},
        format="json",
    )

    assert _error(response) == ("type", "item_create_child_type_folder_only")
    assert not link.children().exists()


def test_api_items_link_update_url():
    """An editor can change the URL of a link, with the same validation as on creation."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    link = factories.ItemFactory(parent=_owned_folder(user), type=models.ItemTypeChoices.LINK)

    response = client.patch(
        f"/api/v1.0/items/{link.id!s}/", {"link_url": "http://example.org/"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["link_url"] == "http://example.org/"
    link.refresh_from_db()
    assert link.link_url == "http://example.org/"

    for link_url in ["javascript:alert(1)", None, ""]:
        response = client.patch(
            f"/api/v1.0/items/{link.id!s}/", {"link_url": link_url}, format="json"
        )
        assert _error(response)[0] == "link_url"

    link.refresh_from_db()
    assert link.link_url == "http://example.org/"


def test_api_items_link_update_url_forbidden_on_other_types():
    """The link_url of a folder or a file cannot be set."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    folder = _owned_folder(user)

    response = client.patch(
        f"/api/v1.0/items/{folder.id!s}/", {"link_url": LINK_URL}, format="json"
    )

    assert _error(response) == ("link_url", "item_update_link_url_only_allowed_for_links")
    folder.refresh_from_db()
    assert folder.link_url is None


def test_api_items_link_filter_type():
    """The type filter returns links."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    folder = _owned_folder(user)
    link = factories.ItemFactory(parent=folder, type=models.ItemTypeChoices.LINK)
    factories.ItemFactory(parent=folder, type=models.ItemTypeChoices.FOLDER)

    response = client.get(f"/api/v1.0/items/{folder.id!s}/children/?type=link")

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["results"]] == [str(link.id)]


def test_models_items_link_url_enforced_on_save():
    """The model refuses a link without a valid URL and a URL on any other type."""
    with pytest.raises(ValidationError) as excinfo:
        factories.ItemFactory(type=models.ItemTypeChoices.LINK, link_url=None)
    assert excinfo.value.message_dict["link_url"] == ["A link URL is required for links."]

    with pytest.raises(ValidationError) as excinfo:
        factories.ItemFactory(type=models.ItemTypeChoices.LINK, link_url="javascript:alert(1)")
    assert "link_url" in excinfo.value.message_dict

    with pytest.raises(ValidationError) as excinfo:
        factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, link_url=LINK_URL)
    assert excinfo.value.message_dict["link_url"] == ["A link URL is only allowed for links."]


def test_models_items_link_url_enforced_by_the_database():
    """Bulk updates bypassing save() still cannot break the link_url invariant."""
    link = factories.ItemFactory(type=models.ItemTypeChoices.LINK)
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    for queryset, values in [
        (models.Item.objects.filter(pk=link.pk), {"link_url": None}),
        (models.Item.objects.filter(pk=link.pk), {"link_url": "javascript:alert(1)"}),
        (models.Item.objects.filter(pk=folder.pk), {"link_url": LINK_URL}),
    ]:
        with pytest.raises(IntegrityError), transaction.atomic():
            queryset.update(**values)
