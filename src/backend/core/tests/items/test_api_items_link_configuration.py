"""Tests for link configuration of items on API endpoint"""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", models.LinkRoleChoices.values)
@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
def test_api_items_link_configuration_update_anonymous(reach, role):
    """Anonymous users should not be allowed to update a link configuration."""
    item = factories.ItemFactory(link_reach=reach, link_role=role)
    old_item_values = serializers.LinkItemSerializer(instance=item).data

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data
    response = APIClient().put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )
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

    item.refresh_from_db()
    item_values = serializers.LinkItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("role", models.LinkRoleChoices.values)
@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
def test_api_items_link_configuration_update_authenticated_unrelated(reach, role):
    """
    Authenticated users should not be allowed to update the link configuration for
    an item to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach=reach, link_role=role)
    old_item_values = serializers.LinkItemSerializer(instance=item).data

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
    }

    item.refresh_from_db()
    item_values = serializers.LinkItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("role", ["editor", "reader"])
@pytest.mark.parametrize("via", VIA)
def test_api_items_link_configuration_update_authenticated_related_forbidden(
    via, role, mock_user_teams
):
    """
    Users who are readers or editors of an item should not be allowed to update
    the link configuration.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    old_item_values = serializers.LinkItemSerializer(instance=item).data

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
    }

    item.refresh_from_db()
    item_values = serializers.LinkItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("role", ["administrator", "owner"])
@pytest.mark.parametrize("via", VIA)
def test_api_items_link_configuration_update_authenticated_related_success(
    via,
    role,
    mock_user_teams,
):
    """
    A user who is administrator or owner of an item should be allowed to update
    the link configuration.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.AUTHENTICATED,
        link_role=models.LinkRoleChoices.READER,
    )
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory(
            link_reach=models.LinkReachChoices.PUBLIC,
            link_role=models.LinkRoleChoices.EDITOR,
        )
    ).data

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )
    assert response.status_code == 200

    item = models.Item.objects.get(pk=item.pk)
    item_values = serializers.LinkItemSerializer(instance=item).data
    for key, value in item_values.items():
        assert value == new_item_values[key]


def test_api_items_link_configuration_update_role_restricted_forbidden():
    """
    Test that trying to set link_role on an item with restricted link_reach
    returns a validation error.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.OWNER)

    # Try to set a meaningful role on a restricted item
    new_data = {
        "link_reach": models.LinkReachChoices.RESTRICTED,
        "link_role": models.LinkRoleChoices.EDITOR,
    }

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_data,
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "link_role",
                "code": "invalid",
                "detail": (
                    "Cannot set link_role when link_reach is 'restricted'. "
                    "Link role must be null for restricted reach."
                ),
            }
        ],
        "type": "validation_error",
    }


def test_api_items_link_configuration_update_link_reach_required():
    """
    Test that link_reach is required when updating link configuration.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.PUBLIC,
        link_role=models.LinkRoleChoices.READER,
    )

    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.OWNER)

    # Try to update without providing link_reach
    new_data = {"link_role": models.LinkRoleChoices.EDITOR}

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_data,
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "link_reach",
                "code": "invalid",
                "detail": "This field is required.",
            }
        ],
        "type": "validation_error",
    }


def test_api_items_link_configuration_update_restricted_without_role_success():
    """
    Test that setting link_reach to restricted without specifying link_role succeeds.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.PUBLIC,
        link_role=models.LinkRoleChoices.READER,
    )

    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.OWNER)

    # Only specify link_reach, not link_role
    new_data = {
        "link_reach": models.LinkReachChoices.RESTRICTED,
    }

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_data,
        format="json",
    )

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.link_reach == models.LinkReachChoices.RESTRICTED


@pytest.mark.parametrize(
    "reach", [models.LinkReachChoices.PUBLIC, models.LinkReachChoices.AUTHENTICATED]
)
@pytest.mark.parametrize("role", models.LinkRoleChoices.values)
def test_api_items_link_configuration_update_non_restricted_with_valid_role_success(
    reach,
    role,
):
    """
    Test that setting non-restricted link_reach with valid link_role succeeds.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.OWNER)

    new_data = {
        "link_reach": reach,
        "link_role": role,
    }

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_data,
        format="json",
    )

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.link_reach == reach
    assert item.link_role == role


def test_api_items_link_configuration_update_with_ancestor_constraints():
    """
    Test that link configuration respects ancestor constraints using get_select_options.
    This test may need adjustment based on the actual get_select_options implementation.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent_item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.PUBLIC,
        link_role=models.LinkRoleChoices.READER,
        type=models.ItemTypeChoices.FOLDER,
    )

    child_item = factories.ItemFactory(
        parent=parent_item,
        link_reach=models.LinkReachChoices.PUBLIC,
        link_role=models.LinkRoleChoices.READER,
        type=models.ItemTypeChoices.FILE,
    )

    factories.UserItemAccessFactory(
        item=child_item, user=user, role=models.RoleChoices.OWNER
    )

    # Try to set child to PUBLIC when parent is RESTRICTED
    new_data = {
        "link_reach": models.LinkReachChoices.RESTRICTED,
        "link_role": models.LinkRoleChoices.READER,
    }

    response = client.put(
        f"/api/v1.0/items/{child_item.id!s}/link-configuration/",
        new_data,
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "link_reach",
                "code": "invalid",
                "detail": (
                    "Link reach 'restricted' is not allowed based on parent item configuration."
                ),
            }
        ],
        "type": "validation_error",
    }


def test_api_items_link_configuration_update_invalid_role_for_reach_validation():
    """
    Test the specific validation logic that checks if link_role is allowed for link_reach.
    This tests the code section that validates allowed_roles from get_select_options.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent_item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.AUTHENTICATED,
        link_role=models.LinkRoleChoices.EDITOR,
        type=models.ItemTypeChoices.FOLDER,
    )

    child_item = factories.ItemFactory(
        parent=parent_item,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
        type=models.ItemTypeChoices.FOLDER,
    )

    factories.UserItemAccessFactory(
        item=child_item, user=user, role=models.RoleChoices.OWNER
    )

    new_data = {
        "link_reach": models.LinkReachChoices.AUTHENTICATED,
        "link_role": models.LinkRoleChoices.READER,  # This should be rejected
    }

    response = client.put(
        f"/api/v1.0/items/{child_item.id!s}/link-configuration/",
        new_data,
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "link_role",
                "code": "invalid",
                "detail": (
                    "Link role 'reader' is not allowed for link reach 'authenticated'. "
                    "Allowed roles: editor"
                ),
            }
        ],
        "type": "validation_error",
    }


def test_api_items_link_configuration_sync_link_reach_descendants():
    """
    When updating the link configuration of an item, sync the link reach of the descendants
    when the updated link reach is higher than the previous one.
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    folder1 = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
        title="Folder 1",
    )
    folder2 = factories.ItemFactory(
        parent=folder1,
        type=models.ItemTypeChoices.FOLDER,
        title="Folder 2",
        link_reach=None,
    )
    folder3 = factories.ItemFactory(
        parent=folder2,
        type=models.ItemTypeChoices.FOLDER,
        title="Folder 3",
        link_reach=None,
    )

    assert folder1.link_reach == models.LinkReachChoices.RESTRICTED
    assert folder1.computed_link_reach == models.LinkReachChoices.RESTRICTED

    assert folder2.link_reach is None
    assert folder2.computed_link_reach == models.LinkReachChoices.RESTRICTED

    assert folder3.link_reach is None
    assert folder3.computed_link_reach == models.LinkReachChoices.RESTRICTED

    # First update folder 2 to authenticated

    response = client.put(
        f"/api/v1.0/items/{folder2.id!s}/link-configuration/",
        {
            "link_reach": models.LinkReachChoices.AUTHENTICATED,
            "link_role": folder2.link_role,
        },
        format="json",
    )
    assert response.status_code == 200

    # in order to remove all computed values, we need to create a new item instance
    folder1 = models.Item.objects.get(pk=folder1.pk)
    folder2 = models.Item.objects.get(pk=folder2.pk)
    folder3 = models.Item.objects.get(pk=folder3.pk)

    assert folder1.link_reach == models.LinkReachChoices.RESTRICTED
    assert folder1.computed_link_reach == models.LinkReachChoices.RESTRICTED

    assert folder2.link_reach == models.LinkReachChoices.AUTHENTICATED
    assert folder2.computed_link_reach == models.LinkReachChoices.AUTHENTICATED

    assert folder3.link_reach is None
    assert folder3.computed_link_reach == models.LinkReachChoices.AUTHENTICATED

    # Then update folder 3 to public
    response = client.put(
        f"/api/v1.0/items/{folder3.id!s}/link-configuration/",
        {
            "link_reach": models.LinkReachChoices.PUBLIC,
            "link_role": folder3.link_role,
        },
        format="json",
    )
    assert response.status_code == 200

    # in order to remove all computed values, we need to create a new item instance
    folder1 = models.Item.objects.get(pk=folder1.pk)
    folder2 = models.Item.objects.get(pk=folder2.pk)
    folder3 = models.Item.objects.get(pk=folder3.pk)

    assert folder1.link_reach == models.LinkReachChoices.RESTRICTED
    assert folder1.computed_link_reach == models.LinkReachChoices.RESTRICTED

    assert folder2.link_reach == models.LinkReachChoices.AUTHENTICATED
    assert folder2.computed_link_reach == models.LinkReachChoices.AUTHENTICATED

    assert folder3.link_reach == models.LinkReachChoices.PUBLIC
    assert folder3.computed_link_reach == models.LinkReachChoices.PUBLIC

    # Finally update folder 1 to public, all descendants should be in sync with it
    response = client.put(
        f"/api/v1.0/items/{folder1.id!s}/link-configuration/",
        {
            "link_reach": models.LinkReachChoices.PUBLIC,
            "link_role": folder1.link_role,
        },
        format="json",
    )
    assert response.status_code == 200

    # in order to remove all computed values, we need to create a new item instance
    folder1 = models.Item.objects.get(pk=folder1.pk)
    folder2 = models.Item.objects.get(pk=folder2.pk)
    folder3 = models.Item.objects.get(pk=folder3.pk)

    assert folder1.link_reach == models.LinkReachChoices.PUBLIC
    assert folder1.computed_link_reach == models.LinkReachChoices.PUBLIC

    assert folder2.link_reach is None
    assert folder2.computed_link_reach == models.LinkReachChoices.PUBLIC

    assert folder3.link_reach is None
    assert folder3.computed_link_reach == models.LinkReachChoices.PUBLIC
