"""
Tests for the scope based permissions of the external API, for requests authenticated
through Menshen token exchange.

Where the resource server opens the external API to an allowlist of audiences, an
exchanged token carries scopes, and MENSHEN_REQUIRED_SCOPES maps each action to the
scope it demands. An action left out of that mapping is never reachable.
"""

from types import SimpleNamespace

import pytest

from core.external_api.authentication import MenshenAuthentication
from core.external_api.permissions import MenshenPermission

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
    settings.MENSHEN_REQUIRED_SCOPES = {"items": {"children": {"GET": "drive:item:list-children"}}}
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
