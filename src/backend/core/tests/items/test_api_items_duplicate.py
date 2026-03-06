"""
Test the item duplicate action API endpoint in drive's core app.
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


def test_api_items_duplicate_anonymous_user():
    """Anonymous users should not be able to duplicate items."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach="public",
        link_role="editor",
    )

    response = APIClient().post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 401
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
            },
        ],
        "type": "client_error",
    }


def test_api_items_duplicate_authenticated_no_access():
    """Authenticated users without any access to an item should not be able to duplicate it."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )

    response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 403


@pytest.mark.parametrize("role", ["reader"])
def test_api_items_duplicate_authenticated_insufficient_role(role):
    """
    Authenticated users with reader role should not be able to duplicate items.
    The duplicate ability requires at least editor role.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, role)],
    )

    response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 403


@pytest.mark.parametrize("role", ["editor", "administrator", "owner"])
def test_api_items_duplicate_authenticated_sufficient_role(role):
    """
    Authenticated users with editor, administrator or owner role should be able
    to duplicate a ready file item.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="text/plain",
        filename="myfile.txt",
        description="A description",
        users=[(user, role)],
    )

    with mock.patch("core.tasks.item.duplicate_file.delay") as mock_delay:
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 201
    response_data = response.json()

    # The task should have been triggered
    mock_delay.assert_called_once()

    # The duplicated item should be a different object
    assert response_data["id"] != str(item.id)

    # The duplicated item should have the same title, mimetype, filename, description
    assert response_data["title"] == item.title
    assert response_data["mimetype"] == item.mimetype
    assert response_data["filename"] == item.filename
    assert response_data["description"] == item.description
    assert response_data["type"] == models.ItemTypeChoices.FILE

    # A new item should exist in the database
    duplicated_item = models.Item.objects.get(id=response_data["id"])
    assert duplicated_item.creator == user


@pytest.mark.parametrize("via", VIA)
def test_api_items_duplicate_via_user_or_team(via, mock_user_teams):
    """Users with access via a user or team role should be able to duplicate items."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )

    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role="editor")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role="editor")

    with mock.patch("core.tasks.item.duplicate_file.delay") as mock_delay:
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 201
    mock_delay.assert_called_once()


def test_api_items_duplicate_folder_not_allowed():
    """Folders cannot be duplicated."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )

    response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "upload_state",
    [
        *(
            state
            for state in models.ItemUploadStateChoices.values
            if state
            not in [
                models.ItemUploadStateChoices.READY,
                models.ItemUploadStateChoices.SUSPICIOUS,
            ]
        ),
    ],
)
def test_api_items_duplicate_non_ready_file_not_allowed(upload_state):
    """Only files with upload_state=READY can be duplicated."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        users=[(user, "owner")],
        update_upload_state=upload_state,
    )

    response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 403


def test_api_items_duplicate_suspicious_file_not_allowed():
    """
    Files with SUSPICIOUS upload_state cannot be duplicated.
    Suspicious items are only visible to their creator, so a non-creator owner
    gets a 404.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # The user is the creator so the item is accessible, but SUSPICIOUS means
    # the duplicate ability is not granted (upload_state != READY).
    item = factories.ItemFactory(
        creator=user,
        type=models.ItemTypeChoices.FILE,
        users=[(user, "owner")],
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
    )

    response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 403


def test_api_items_duplicate_in_folder():
    """
    Duplicating a file that lives inside a folder should place the duplicate
    in the same folder.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent_folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, "owner")],
        parent=parent_folder,
    )

    with mock.patch("core.tasks.item.duplicate_file.delay") as mock_delay:
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 201
    mock_delay.assert_called_once()

    duplicated_item = models.Item.objects.get(id=response.json()["id"])

    # The duplicate should be in the same folder as the original
    assert duplicated_item.parent() == parent_folder


def test_api_items_duplicate_at_root():
    """
    Duplicating a file at root level should place the duplicate at root level
    with link_reach set to RESTRICTED.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, "owner")],
    )

    with mock.patch("core.tasks.item.duplicate_file.delay") as mock_delay:
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 201
    mock_delay.assert_called_once()

    duplicated_item = models.Item.objects.get(id=response.json()["id"])

    # The duplicate should be at root level (no parent)
    assert duplicated_item.parent() is None
    assert duplicated_item.link_reach == models.LinkReachChoices.RESTRICTED


def test_api_items_duplicate_celery_task_called_with_correct_args():
    """
    The duplicate_file celery task should be called with the correct item ids.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, "owner")],
    )

    with mock.patch("core.tasks.item.duplicate_file.delay") as mock_delay:
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 201

    duplicated_item_id = response.json()["id"]
    mock_delay.assert_called_once_with(
        item_to_duplicate=item.id,
        duplicated_item=models.Item.objects.get(id=duplicated_item_id).id,
    )


def test_api_items_duplicate_creator_is_requester():
    """
    The user who triggers the duplicate action should become the creator
    of the duplicated item, regardless of the original item's creator.
    """
    original_creator = factories.UserFactory()
    duplicator = factories.UserFactory()
    client = APIClient()
    client.force_login(duplicator)

    item = factories.ItemFactory(
        creator=original_creator,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(original_creator, "owner"), (duplicator, "editor")],
    )

    with mock.patch("core.tasks.item.duplicate_file.delay"):
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 201

    duplicated_item = models.Item.objects.get(id=response.json()["id"])
    assert duplicated_item.creator == duplicator


def test_api_items_duplicate_deleted_item():
    """Deleted items should not be duplicable."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, "owner")],
    )
    item.soft_delete()

    response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 403
