"""Tests for the access service"""

from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

import pytest

from core.factories import ItemFactory, UserFactory, UserItemAccessFactory
from core.models import LinkReachChoices
from wopi.services.access import (
    AccessUserItem,
    AccessUserItemInvalidDataError,
    AccessUserItemNotAllowed,
    AccessUserItemNotFoundError,
    AccessUserItemService,
    timezone,
)

pytestmark = pytest.mark.django_db


def test_access_user_item_to_dict():
    """Test the to_dict method of the AccessUserItem class."""
    item = ItemFactory()
    user = UserFactory()
    access_user_item = AccessUserItem(item=item, user=user)
    assert access_user_item.to_dict() == {
        "item": str(item.id),
        "user": str(user.id),
    }


def test_access_user_item_to_dict_with_anonymous_user():
    """Test the to_dict method of the AccessUserItem class with an anonymous user."""
    item = ItemFactory()
    access_user_item = AccessUserItem(item=item, user=AnonymousUser())
    assert access_user_item.to_dict() == {
        "item": str(item.id),
        "user": None,
    }


def test_access_user_item_from_dict():
    """Test the from_dict method of the AccessUserItem class."""
    item = ItemFactory()
    user = UserFactory()
    data = {
        "item": str(item.id),
        "user": str(user.id),
    }
    access_user_item = AccessUserItem.from_dict(data)
    assert access_user_item.item == item
    assert access_user_item.user == user


def test_access_user_item_from_dict_with_anonymous_user():
    """Test the from_dict method of the AccessUserItem class with an anonymous user."""
    item = ItemFactory()
    data = {
        "item": str(item.id),
        "user": None,
    }
    access_user_item = AccessUserItem.from_dict(data)
    assert access_user_item.item == item
    assert isinstance(access_user_item.user, AnonymousUser)


def test_access_user_item_from_dict_with_nonexistent_item():
    """Test the from_dict method of the AccessUserItem class with a nonexistent item."""
    data = {
        "item": "00000000-0000-0000-0000-000000000000",
        "user": None,
    }
    with pytest.raises(AccessUserItemNotFoundError):
        AccessUserItem.from_dict(data)


def test_access_user_item_from_dict_with_nonexistent_user():
    """Test the from_dict method of the AccessUserItem class with a nonexistent user."""
    item = ItemFactory()
    data = {
        "item": str(item.id),
        "user": "00000000-0000-0000-0000-000000000000",
    }
    with pytest.raises(AccessUserItemNotFoundError):
        AccessUserItem.from_dict(data)


def test_access_user_item_from_dict_with_invalid_data():
    """Test the from_dict method of the AccessUserItem class with invalid data."""
    item = ItemFactory()

    # Missing item key
    data = {
        "user": None,
    }
    with pytest.raises(AccessUserItemInvalidDataError):
        AccessUserItem.from_dict(data)

    # Missing user key
    data = {
        "item": str(item.id),
    }
    with pytest.raises(AccessUserItemInvalidDataError):
        AccessUserItem.from_dict(data)

    # Invalid item format
    data = {
        "item": "not-a-uuid",
        "user": None,
    }
    with pytest.raises(AccessUserItemInvalidDataError):
        AccessUserItem.from_dict(data)


# AccessUserItemService


def test_access_user_item_service_insert_user_and_item(settings):
    """
    Inserting a new access token for a user and item should return an access token and
    access token ttl.
    """

    settings.WOPI_ACCESS_TOKEN_TIMEOUT = 60
    access = UserItemAccessFactory()

    with patch.object(timezone, "now", return_value=datetime(2025, 3, 10, 12, 0, 0)):
        access_user_item_service = AccessUserItemService()
        access_token, access_token_ttl = access_user_item_service.insert_new_access(
            access.item, access.user
        )

    assert access_token is not None
    assert access_token_ttl == 1741608060000

    assert cache.get(access_token) is not None


def test_access_user_item_service_insert_user_and_item_with_anonymous_user(settings):
    """
    Inserting a new access token for an anonymous user and item should return an access token and
    access token ttl.
    """
    settings.WOPI_ACCESS_TOKEN_TIMEOUT = 60
    item = ItemFactory(link_reach="public")
    user = AnonymousUser()

    with patch.object(timezone, "now", return_value=datetime(2025, 3, 10, 12, 0, 0)):
        access_user_item_service = AccessUserItemService()
        access_token, access_token_ttl = access_user_item_service.insert_new_access(
            item, user
        )

    assert access_token is not None
    assert access_token_ttl == 1741608060000

    assert cache.get(access_token) is not None


@pytest.mark.parametrize(
    "link_reach",
    [LinkReachChoices.AUTHENTICATED, LinkReachChoices.RESTRICTED],
)
def test_access_user_item_service_insert_anonymous_user_with_no_access(link_reach):
    """
    Inserting a new access token for an anonymous user and item with no access should raise
    an AccessUserItemNotAllowed exception.
    """
    item = ItemFactory(link_reach=link_reach)
    user = AnonymousUser()

    with pytest.raises(AccessUserItemNotAllowed):
        access_user_item_service = AccessUserItemService()
        access_user_item_service.insert_new_access(item, user)


def test_access_user_item_service_user_not_allowed():
    """
    Inserting a new access token for a user and item with no access should raise an
    AccessUserItemNotAllowed exception.
    """
    user = UserFactory()
    item = ItemFactory(link_reach=LinkReachChoices.RESTRICTED)

    with pytest.raises(AccessUserItemNotAllowed):
        access_user_item_service = AccessUserItemService()
        access_user_item_service.insert_new_access(item, user)


def test_access_user_item_service_retrieve_data():
    """
    Retrieve the data of an access token.
    """
    access = UserItemAccessFactory()

    access_user_item_service = AccessUserItemService()
    access_token, _ = access_user_item_service.insert_new_access(
        access.item, access.user
    )

    access_user_item = access_user_item_service.get_access_user_item(access_token)

    assert access_user_item.item == access.item
    assert access_user_item.user == access.user

    # create a new access token for the same user
    new_access_token, _ = access_user_item_service.insert_new_access(
        access.item, access.user
    )

    assert new_access_token != access_token


def test_access_user_item_service_retrieve_data_with_invalid_token():
    """
    Retrieve the data of an invalid access token.
    """
    access_user_item_service = AccessUserItemService()

    with pytest.raises(AccessUserItemNotFoundError):
        access_user_item_service.get_access_user_item("invalid-token")
