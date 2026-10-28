"""
Tests for the entitlements check on the external API authenticated through Menshen.

The interactive login refuses a user the entitlements backend does not grant access
to. These tests pin that an exchanged token is not a way around that check, all the
more so as it is the one path that provisions users Drive has never seen.
"""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.tests.utils.menshen import MENSHEN_SUB, MENSHEN_TOKEN

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument

# The body the standardized error handler renders when the entitlements backend refuses.
REFUSED = {
    "type": "client_error",
    "errors": [
        {
            "code": "permission_denied",
            "detail": "User does not have access to the app",
            "attr": None,
        }
    ],
}


def set_can_access(settings, can_access):
    """Point the entitlements backend at a static can_access decision."""
    settings.ENTITLEMENTS_BACKEND = "core.entitlements.backends.static.StaticEntitlementsBackend"
    settings.ENTITLEMENTS_BACKEND_PARAMETERS = {
        "entitlements": {
            "can_access": {"result": can_access},
            "can_upload": {"result": True},
        }
    }


def build_client():
    """Build an API client carrying an exchanged token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {MENSHEN_TOKEN}")

    return client


def test_api_items_list_menshen_entitled_user(
    menshen_backend_conf, menshen_backend, user_specific_sub
):
    """An entitled user should be allowed to list items with an exchanged token."""
    set_can_access(menshen_backend_conf, True)
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.READER
    )

    response = build_client().get("/external_api/v1.0/items/")

    assert response.status_code == 200


def test_api_items_list_menshen_user_not_entitled(
    menshen_backend_conf, menshen_backend, user_specific_sub
):
    """A user the entitlements backend refuses should not reach the external API."""
    set_can_access(menshen_backend_conf, False)
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.READER
    )

    response = build_client().get("/external_api/v1.0/items/")

    assert response.status_code == 403
    # Refused for the entitlement, not for a missing scope or a missing access.
    assert response.json() == REFUSED


def test_api_items_list_menshen_unknown_user_not_entitled(menshen_backend_conf, menshen_backend):
    """A user Drive has never seen should be provisioned, then refused.

    The account is created before the check, as it is on the interactive login: the
    entitlements backend needs a user to decide on.
    """
    set_can_access(menshen_backend_conf, False)

    response = build_client().get("/external_api/v1.0/items/")

    assert response.status_code == 403
    assert response.json() == REFUSED
    assert models.User.objects.filter(sub=MENSHEN_SUB).exists()
