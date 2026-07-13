"""
Test Entitlements API endpoints with DeployCenter entitlements backend.
"""

import urllib.parse

from django.test import override_settings

import pytest
import responses
from rest_framework.test import APIClient

from core import factories
from core.entitlements.backends.deploycenter import DeployCenterEntitlementsBackend

pytestmark = pytest.mark.django_db

ENTITLEMENTS_URL = "http://backend-dev:8000/api/v1.0/entitlements/"
ENTITLEMENTS_BACKEND_PARAMETERS = {
    "base_url": ENTITLEMENTS_URL,
    "api_key": "3e489c7c0029cf448c4d965de0c69ed11706aac46767be6138f44cabe4cf8d42",
    "service_id": 8,
    "oidc_claims": ["siret"],
}


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
def test_api_entitlements_deploycenter_get_entitlements_anonymous():
    """Anonymous users should not be allowed to get entitlements."""
    client = APIClient()
    response = client.get("/api/v1.0/entitlements/")
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


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_both_true():
    """Authenticated users should get entitlements when both can_access and can_upload are True."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "21140001500015"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_can_upload_false():
    """Authenticated users should get correct entitlements when can_upload is False."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_reason": "not_activated",
            },
            "organization": "ACME",
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": False,
            "reason": "not_activated",
        },
        "context": {
            "organization": "ACME",
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_can_access_false():
    """Authenticated users should get correct entitlements when can_access is False."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": False,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": False,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_get_entitlements_cache():
    """Authenticated users should get entitlements from cache when doing subsequent requests."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith(ENTITLEMENTS_URL)
    assert "siret" in responses.calls[0].request.url
    assert f"account_email={urllib.parse.quote(user.email)}" in responses.calls[0].request.url
    assert "account_type=user" in responses.calls[0].request.url
    assert "service_id=8" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["X-Service-Auth"] == (
        f"Bearer {ENTITLEMENTS_BACKEND_PARAMETERS['api_key']}"
    )

    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
            "reason": None,
        },
        "quota": {
            "state": "default",
            "usage": 25000000,
            "limit": 100000000,
        },
        "context": {
            "organization": None,
            "operator": None,
            "potentialOperators": None,
        },
    }
    # Verify that the request was not made again.
    assert len(responses.calls) == 1


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
@pytest.mark.parametrize("reason", ["no_organization", "not_activated"])
def test_api_entitlements_deploycenter_quota_hidden(reason):
    """The quota gauge should be hidden when the service is not usable by the user."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_reason": reason,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert "quota" not in response.json()
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": reason,
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_quota_organization_excedeed():
    """The quota gauge should be locked when the organization quota is reached."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_resolve_level": "organization",
                "max_storage_organization": 100000000,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["quota"] == {
        "state": "excedeed_locked",
        "reason": "organization_quota_excedeed",
    }
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": "organization_quota_excedeed",
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_quota_error_metric_account_not_found():
    """The quota gauge should be in error when the account metrics are missing."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
                "max_storage_account": 100000000,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["quota"] == {
        "state": "error",
        "error": "metric_account_not_found",
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_quota_error_max_storage_account_not_found():
    """The quota gauge should be in error when the account storage limit is missing."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": True,
            },
            "metrics": {
                "account": {
                    "storage_used": 25000000,
                },
            },
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["quota"] == {
        "state": "error",
        "error": "max_storage_account_not_found",
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
@pytest.mark.parametrize(
    "resolve_level,expected_reason",
    [
        ("user", "user_quota_excedeed"),
        ("user_override", "user_override_quota_excedeed"),
        ("organization", "organization_quota_excedeed"),
    ],
)
def test_api_entitlements_deploycenter_can_upload_reason_from_resolve_level(
    resolve_level, expected_reason
):
    """When no explicit reason is given, it should be derived from the resolve level."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_resolve_level": resolve_level,
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": expected_reason,
    }


@override_settings(
    ENTITLEMENTS_BACKEND="core.entitlements.backends.deploycenter.DeployCenterEntitlementsBackend",
    ENTITLEMENTS_BACKEND_PARAMETERS=ENTITLEMENTS_BACKEND_PARAMETERS,
)
@responses.activate
def test_api_entitlements_deploycenter_can_upload_explicit_reason_wins():
    """An explicit reason should take precedence over the resolve level fallback."""
    responses.add(
        responses.GET,
        ENTITLEMENTS_URL,
        json={
            "entitlements": {
                "can_access": True,
                "can_upload": False,
                "can_upload_reason": "not_activated",
                "can_upload_resolve_level": "user",
            }
        },
        status=200,
    )

    client = APIClient()
    user = factories.UserFactory(claims={"siret": "12345678901234"})
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json()["can_upload"] == {
        "result": False,
        "reason": "not_activated",
    }


def test_api_entitlements_deploycenter_missing_base_url_parameter():
    """Missing base_url parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(  # pylint: disable=no-value-for-parameter
            service_id=8,
            api_key="secret",
        )


def test_api_entitlements_deploycenter_missing_api_key_parameter():
    """Missing api_key parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(  # pylint: disable=no-value-for-parameter
            base_url=ENTITLEMENTS_URL,
            service_id=8,
        )


def test_api_entitlements_deploycenter_missing_service_id_parameter():
    """Missing service_id parameter should raise an exception."""
    with pytest.raises(TypeError):
        DeployCenterEntitlementsBackend(  # pylint: disable=no-value-for-parameter
            base_url=ENTITLEMENTS_URL,
            api_key="secret",
        )
