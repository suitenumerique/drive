"""
Tests for the scope based permissions of the external API, for requests authenticated
through Menshen token exchange.

Where the resource server opens the external API to an allowlist of audiences, an
exchanged token carries scopes, and MENSHEN_REQUIRED_SCOPES maps each action to the
scope it demands. An action left out of that mapping is never reachable.
"""

from types import SimpleNamespace

import pytest
import responses
from rest_framework.test import APIClient

from core import factories, models
from core.external_api.authentication import MenshenAuthentication
from core.external_api.permissions import MenshenPermission
from core.tests.utils.menshen import (
    MENSHEN_INTROSPECTION_URL,
    MENSHEN_TOKEN,
    menshen_introspection_response,
)

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument

EXTERNAL_API_ACTIONS = ["create", "list", "retrieve", "children", "upload_ended"]

# Tells "no authenticator given, use Menshen" apart from "no authenticator at all".
UNSET = object()


def build_request(scopes=None, authenticator=UNSET, method="GET"):
    """Build the request attributes the permission reads."""
    return SimpleNamespace(
        successful_authenticator=(
            MenshenAuthentication() if authenticator is UNSET else authenticator
        ),
        auth=None if scopes is None else {"scope": scopes},
        method=method,
    )


def build_view(action, resource="items", actions=EXTERNAL_API_ACTIONS):
    """Build the view attributes the permission reads."""
    view = SimpleNamespace(action=action, resource=resource)

    if actions is not None:
        view.resource_server_actions = actions

    return view


def menshen_client(rsps, scope):
    """Build an API client whose exchanged token carries the given scopes."""
    rsps.add(
        responses.POST,
        MENSHEN_INTROSPECTION_URL,
        json=menshen_introspection_response(scope=scope),
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {MENSHEN_TOKEN}")

    return client


# The permission class


def test_permission_refuses_another_authentication_backend(settings):
    """A request that did not come through Menshen is none of this permission's business."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request(["drive:item:list"], authenticator=SimpleNamespace())

    assert MenshenPermission().has_permission(request, build_view("list")) is False


def test_permission_refuses_an_unauthenticated_request(settings):
    """A request that carries no successful authenticator should be refused."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request(["drive:item:list"], authenticator=None)

    assert MenshenPermission().has_permission(request, build_view("list")) is False


def test_permission_leaves_unsupported_methods_to_the_router(settings):
    """A method the route does not serve should answer 405, not 403."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request([], method="PUT")

    assert MenshenPermission().has_permission(request, build_view(None)) is True


def test_permission_refuses_an_action_the_external_api_does_not_open(settings):
    """An action outside EXTERNAL_API should stay out of reach, scope or not."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"destroy": "drive:item:destroy"}}
    request = build_request(["drive:item:destroy"])

    assert MenshenPermission().has_permission(request, build_view("destroy")) is False


def test_permission_refuses_an_action_absent_from_the_mapping(settings):
    """An action left out of MENSHEN_REQUIRED_SCOPES should never be reachable."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"retrieve": "drive:item:retrieve"}}
    request = build_request(["drive:item:list", "drive:item:retrieve"])

    assert MenshenPermission().has_permission(request, build_view("list")) is False


def test_permission_shipped_default_grants_nothing():
    """The default MENSHEN_REQUIRED_SCOPES is empty, so it should open no action."""
    request = build_request(["drive:item:list"])

    for action in EXTERNAL_API_ACTIONS:
        assert MenshenPermission().has_permission(request, build_view(action)) is False


def test_permission_grants_an_action_whose_scope_the_token_carries(settings):
    """The mapped scope being present should grant the action."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request(["drive:item:list", "something:else"])

    assert MenshenPermission().has_permission(request, build_view("list")) is True


def test_permission_refuses_an_action_whose_scope_the_token_lacks(settings):
    """Another scope should not stand in for the one the action demands."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request(["drive:item:retrieve"])

    assert MenshenPermission().has_permission(request, build_view("list")) is False


@pytest.mark.parametrize(
    "method,scopes,expected",
    [
        ("GET", ["drive:item:list-children"], True),
        ("GET", ["drive:item:create-children"], False),
        ("POST", ["drive:item:create-children"], True),
        ("POST", ["drive:item:list-children"], False),
    ],
)
def test_permission_maps_each_method_of_an_action_to_its_own_scope(
    settings, method, scopes, expected
):
    """Listing and creating children should demand their own scopes."""
    settings.MENSHEN_REQUIRED_SCOPES = {
        "items": {
            "children": {
                "GET": "drive:item:list-children",
                "POST": "drive:item:create-children",
            }
        }
    }
    request = build_request(scopes, method=method)

    assert MenshenPermission().has_permission(request, build_view("children")) is expected


def test_permission_refuses_a_method_the_mapping_does_not_cover(settings):
    """A per method mapping should refuse a method it says nothing about.

    HEAD reaches the action that serves GET, but keeps its own method, so it falls
    through the mapping and is refused where GET would be granted.
    """
    settings.MENSHEN_REQUIRED_SCOPES = {
        "items": {"children": {"GET": "drive:item:list-children"}}
    }
    request = build_request(["drive:item:list-children"], method="HEAD")

    assert MenshenPermission().has_permission(request, build_view("children")) is False


def test_permission_refuses_the_metadata_action(settings):
    """OPTIONS resolves to the metadata action, which the external API does not open."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request(["drive:item:list"], method="OPTIONS")

    assert MenshenPermission().has_permission(request, build_view("metadata")) is False


def test_permission_refuses_a_request_without_an_auth_payload(settings):
    """A request carrying no introspection payload should be refused, not crash."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}

    assert MenshenPermission().has_permission(build_request(), build_view("list")) is False


def test_permission_refuses_a_view_without_a_resource(settings):
    """A viewset that declares no resource should map to no scope at all."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request(["drive:item:list"])

    assert MenshenPermission().has_permission(request, build_view("list", resource=None)) is False


def test_permission_skips_the_action_check_for_an_unrestricted_view(settings):
    """A view declaring no resource_server_actions should be gated by scope alone."""
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"list": "drive:item:list"}}
    request = build_request(["drive:item:list"])

    assert MenshenPermission().has_permission(request, build_view("list", actions=None)) is True


# Through the API


def test_api_items_list_with_the_required_scope(menshen_backend_conf, user_specific_sub):
    """A token carrying the list scope should be allowed to list items."""
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.READER
    )

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:list").get("/external_api/v1.0/items/")

    assert response.status_code == 200
    # The token speaks for a user, the listing is that user's own.
    assert str(item.id) in [result["id"] for result in response.json()["results"]]


def test_api_items_list_without_the_required_scope(menshen_backend_conf, user_specific_sub):
    """A token that does not carry the list scope should be refused."""
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.READER
    )

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:retrieve").get("/external_api/v1.0/items/")

    assert response.status_code == 403


def test_api_items_retrieve_with_the_required_scope(menshen_backend_conf, user_specific_sub):
    """A token carrying the retrieve scope should be allowed to retrieve an item."""
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.READER
    )

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:retrieve").get(
            f"/external_api/v1.0/items/{item.id!s}/"
        )

    assert response.status_code == 200


def test_api_items_retrieve_an_item_the_user_cannot_access(
    menshen_backend_conf, user_specific_sub
):
    """The scope should not stand in for the end user's own access to the item.

    The token speaks for a user, the item permissions still apply to that user.
    """
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:retrieve").get(
            f"/external_api/v1.0/items/{item.id!s}/"
        )

    assert response.status_code == 403


def test_api_items_destroy_is_not_reachable(menshen_backend_conf, user_specific_sub):
    """An action the external API does not open should be refused."""
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:destroy").delete(
            f"/external_api/v1.0/items/{item.id!s}/"
        )

    assert response.status_code == 403


def test_api_items_create_children_with_the_required_scope(
    menshen_backend_conf, user_specific_sub
):
    """A token carrying the create-children scope should be allowed to create a child."""
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:create-children").post(
            f"/external_api/v1.0/items/{item.id!s}/children/",
            {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        )

    assert response.status_code == 201


def test_api_items_list_children_scope_does_not_create_children(
    menshen_backend_conf, user_specific_sub
):
    """The scope that lists children should not create any."""
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:list-children").post(
            f"/external_api/v1.0/items/{item.id!s}/children/",
            {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        )

    assert response.status_code == 403
